// Shared domain types used across the app and the API client.

export type Role = 'user' | 'assistant'

export interface Source {
  chunk: string
  source: string
  score: number
  chunk_index?: number
}

export interface ChatMessage {
  role: Role
  content: string
  sources?: Source[]
  pending?: boolean
}

export interface Session {
  id: string
  name: string
  messages: ChatMessage[]
}

export interface DocumentItem {
  file_id: string
  name: string
  uploaded_at?: string
  chunks: number
}

export interface AppConfig {
  llm_provider: string
  embedding_provider?: string
  supported_llm_providers: string[]
  requires_api_key?: boolean
  auth_enabled: boolean
  auth_providers: string[]
}

export interface User {
  id?: string
  name: string
  email: string
}

export interface UploadedFile {
  file_id: string
  name: string
  chunks_indexed: number
  status?: string
}

export interface UploadResponse {
  files: UploadedFile[]
}

export interface ChatResponse {
  answer: string
  sources: Source[]
  session_id: string
}
