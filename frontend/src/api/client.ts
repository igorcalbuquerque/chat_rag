// Thin API client. By default requests go to the same-origin "/api" prefix,
// which Nginx (prod) or the Vite dev proxy forwards to the FastAPI backend.
// In a split deploy (e.g. Render static site + separate backend) set
// VITE_API_BASE_URL to the backend root URL (no "/api"); CORS is open server-side.
import axios, { type AxiosProgressEvent } from 'axios'
import type {
  AppConfig,
  ChatResponse,
  DocumentItem,
  UploadResponse,
  User,
} from '../types'

const API_BASE = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '')

const api = axios.create({ baseURL: API_BASE })

export const API_KEY_STORAGE = 'chat-rag-api-key'
export const PROVIDER_STORAGE = 'chat-rag-llm-provider'
export const AUTH_TOKEN_STORAGE = 'chat-rag-token'

export function getToken(): string {
  return localStorage.getItem(AUTH_TOKEN_STORAGE) || ''
}

export function setToken(token: string): void {
  if (token) localStorage.setItem(AUTH_TOKEN_STORAGE, token)
  else localStorage.removeItem(AUTH_TOKEN_STORAGE)
}

// Optional bring-your-own-key + LLM provider: if the user saved them, send
// per request. The server falls back to its .env config when absent. When
// login is enabled, the signed session token is sent as a bearer header.
function authHeaders(): Record<string, string> {
  const headers: Record<string, string> = {}
  const key = localStorage.getItem(API_KEY_STORAGE)
  const provider = localStorage.getItem(PROVIDER_STORAGE)
  const token = getToken()
  if (key) headers['X-API-Key'] = key
  if (provider) headers['X-LLM-Provider'] = provider
  if (token) headers['Authorization'] = `Bearer ${token}`
  return headers
}

// On an expired/invalid token the server replies 401. Drop the token and let
// the app fall back to the login screen via a global event.
function handleUnauthorized(): void {
  setToken('')
  window.dispatchEvent(new Event('auth:unauthorized'))
}

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) handleUnauthorized()
    return Promise.reject(error)
  },
)

// OAuth helpers (used only when the server reports auth_enabled).
export function loginUrl(provider: string): string {
  return `${API_BASE}/auth/login/${provider}`
}

export async function getMe(): Promise<User> {
  const { data } = await api.get<User>('/auth/me', { headers: authHeaders() })
  return data
}

export async function logout(): Promise<void> {
  setToken('')
  try {
    await api.post('/auth/logout')
  } catch {
    /* best-effort: the token is already cleared client-side */
  }
}

export async function uploadFiles(
  files: File[],
  onProgress?: (pct: number) => void,
  signal?: AbortSignal,
): Promise<UploadResponse> {
  const form = new FormData()
  for (const file of files) form.append('files', file)
  const { data } = await api.post<UploadResponse>('/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data', ...authHeaders() },
    signal, // AbortSignal: lets the caller cancel an in-flight upload
    onUploadProgress: (e: AxiosProgressEvent) => {
      if (onProgress && e.total) onProgress(Math.round((e.loaded / e.total) * 100))
    },
  })
  return data
}

export async function getConfig(): Promise<AppConfig> {
  const { data } = await api.get<AppConfig>('/config')
  return data
}

export async function listDocuments(): Promise<DocumentItem[]> {
  const { data } = await api.get<DocumentItem[]>('/documents', { headers: authHeaders() })
  return data
}

export async function deleteDocument(fileId: string): Promise<{ deleted: boolean }> {
  const { data } = await api.delete<{ deleted: boolean }>(`/documents/${fileId}`, {
    headers: authHeaders(),
  })
  return data
}

export interface ChatParams {
  question: string
  sessionId: string
  topK?: number
}

export async function sendChat({ question, sessionId, topK }: ChatParams): Promise<ChatResponse> {
  const { data } = await api.post<ChatResponse>(
    '/chat',
    { question, session_id: sessionId, top_k: topK },
    { headers: authHeaders() },
  )
  return data
}

export interface StreamHandlers {
  onToken?: (token: string) => void
  onDone?: (payload: ChatResponse) => void
  onError?: (err: unknown) => void
}

// Stream an answer via SSE. Uses fetch (not EventSource) because the endpoint
// is a POST. Invokes onToken for each token and onDone with the final payload.
export async function streamChat(
  { question, sessionId, topK }: ChatParams,
  { onToken, onDone, onError }: StreamHandlers,
): Promise<void> {
  try {
    const response = await fetch(`${API_BASE}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({ question, session_id: sessionId, top_k: topK }),
    })
    if (response.status === 401) handleUnauthorized()
    if (!response.ok || !response.body) throw new Error(`HTTP ${response.status}`)

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let finished = false // saw a terminal event (done or error)

    for (;;) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      const events = buffer.split('\n\n')
      buffer = events.pop() || ''
      for (const block of events) {
        const eventMatch = block.match(/^event: (.+)$/m)
        const dataMatch = block.match(/^data: (.+)$/m)
        if (!dataMatch) continue
        const payload = JSON.parse(dataMatch[1])
        const eventType = eventMatch ? eventMatch[1] : 'message'
        if (eventType === 'token') {
          onToken?.(payload.token)
        } else if (eventType === 'done') {
          finished = true
          onDone?.(payload as ChatResponse)
        } else if (eventType === 'error') {
          // Server reported a generation failure (e.g. the LLM call failed).
          finished = true
          onError?.(new Error(payload.error || 'stream error'))
        }
      }
    }

    // The stream closed without a terminal event: surface it as an error so the
    // caller can stop showing a "thinking" state instead of hanging forever.
    if (!finished) onError?.(new Error('Stream ended without completing.'))
  } catch (err) {
    onError?.(err)
  }
}
