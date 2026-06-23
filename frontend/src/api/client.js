// Thin API client. All requests go to the same-origin "/api" prefix, which
// Nginx (prod) or the Vite dev proxy forwards to the FastAPI backend.
import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export const API_KEY_STORAGE = 'chat-rag-api-key'
export const PROVIDER_STORAGE = 'chat-rag-llm-provider'

// Optional bring-your-own-key + LLM provider: if the user saved them, send
// per request. The server falls back to its .env config when absent.
function authHeaders() {
  const headers = {}
  const key = localStorage.getItem(API_KEY_STORAGE)
  const provider = localStorage.getItem(PROVIDER_STORAGE)
  if (key) headers['X-API-Key'] = key
  if (provider) headers['X-LLM-Provider'] = provider
  return headers
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
    const response = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({ question, session_id: sessionId, top_k: topK }),
    })
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
