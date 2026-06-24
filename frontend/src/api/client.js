// Thin API client. By default requests go to the same-origin "/api" prefix,
// which Nginx (prod) or the Vite dev proxy forwards to the FastAPI backend.
// In a split deploy (e.g. Render static site + separate backend) set
// VITE_API_BASE_URL to the backend root URL (no "/api"); CORS is open server-side.
import axios from 'axios'

const API_BASE = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '')

const api = axios.create({ baseURL: API_BASE })

export const API_KEY_STORAGE = 'chat-rag-api-key'
export const PROVIDER_STORAGE = 'chat-rag-llm-provider'
export const AUTH_TOKEN_STORAGE = 'chat-rag-token'

export function getToken() {
  return localStorage.getItem(AUTH_TOKEN_STORAGE) || ''
}

export function setToken(token) {
  if (token) localStorage.setItem(AUTH_TOKEN_STORAGE, token)
  else localStorage.removeItem(AUTH_TOKEN_STORAGE)
}

// Optional bring-your-own-key + LLM provider: if the user saved them, send
// per request. The server falls back to its .env config when absent. When
// login is enabled, the signed session token is sent as a bearer header.
function authHeaders() {
  const headers = {}
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
function handleUnauthorized() {
  setToken('')
  window.dispatchEvent(new Event('auth:unauthorized'))
}

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) handleUnauthorized()
    return Promise.reject(error)
  },
)

// OAuth helpers (used only when the server reports auth_enabled).
export function loginUrl(provider) {
  return `${API_BASE}/auth/login/${provider}`
}

export async function getMe() {
  const { data } = await api.get('/auth/me')
  return data
}

export async function logout() {
  setToken('')
  try {
    await api.post('/auth/logout')
  } catch {
    /* best-effort: the token is already cleared client-side */
  }
}

export async function uploadFiles(files, onProgress, signal) {
  const form = new FormData()
  for (const file of files) form.append('files', file)
  const { data } = await api.post('/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data', ...authHeaders() },
    signal, // AbortSignal: lets the caller cancel an in-flight upload
    onUploadProgress: (e) => {
      if (onProgress && e.total) onProgress(Math.round((e.loaded / e.total) * 100))
    },
  })
  return data
}

export async function getConfig() {
  const { data } = await api.get('/config')
  return data
}

export async function listDocuments() {
  const { data } = await api.get('/documents')
  return data
}

export async function deleteDocument(fileId) {
  const { data } = await api.delete(`/documents/${fileId}`)
  return data
}

export async function sendChat({ question, sessionId, topK }) {
  const { data } = await api.post(
    '/chat',
    { question, session_id: sessionId, top_k: topK },
    { headers: authHeaders() },
  )
  return data
}

// Stream an answer via SSE. Uses fetch (not EventSource) because the endpoint
// is a POST. Invokes onToken for each token and onDone with the final payload.
export async function streamChat({ question, sessionId, topK }, { onToken, onDone, onError }) {
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

    while (true) {
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
        if (eventType === 'token') onToken?.(payload.token)
        else if (eventType === 'done') onDone?.(payload)
      }
    }
  } catch (err) {
    onError?.(err)
  }
}
