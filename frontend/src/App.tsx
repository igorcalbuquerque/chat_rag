import { useCallback, useEffect, useState } from 'react'
import ApiKeyInput from './components/ApiKeyInput'
import ChatWindow from './components/ChatWindow'
import DocumentList from './components/DocumentList'
import FileUpload from './components/FileUpload'
import LoginScreen from './components/LoginScreen'
import SessionSidebar from './components/SessionSidebar'
import {
  deleteDocument,
  getConfig,
  getMe,
  listDocuments,
  logout as apiLogout,
  setToken,
} from './api/client'
import type { AppConfig, ChatMessage, DocumentItem, Session, User } from './types'

const STORAGE_KEY = 'chat-rag-sessions'

type MessagesUpdater = ChatMessage[] | ((prev: ChatMessage[]) => ChatMessage[])

// If the OAuth callback returned a token in the URL fragment, persist it and
// clean the URL so it doesn't linger in history.
function captureTokenFromHash(): void {
  const hash = window.location.hash
  if (hash.startsWith('#token=')) {
    setToken(decodeURIComponent(hash.slice('#token='.length)))
    window.history.replaceState(null, '', window.location.pathname + window.location.search)
  }
}

function loadSessions(): Session[] | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) return JSON.parse(raw) as Session[]
  } catch {
    /* ignore corrupted storage */
  }
  return null
}

function newSession(name: string): Session {
  return { id: crypto.randomUUID(), name, messages: [] }
}

export default function App() {
  const [sessions, setSessions] = useState<Session[]>(
    () => loadSessions() || [newSession('Conversa 1')],
  )
  const [activeId, setActiveId] = useState<string>(() => sessions[0].id)
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [sidebarOpen, setSidebarOpen] = useState(false) // mobile drawer

  // Auth state. config === null while loading. When auth is disabled the app
  // is open; when enabled, `user` must be set (valid token) to use the app.
  const [config, setConfig] = useState<AppConfig | null>(null)
  const [user, setUser] = useState<User | null>(null)
  const [authReady, setAuthReady] = useState(false)
  // The backend runs on a free tier that sleeps after inactivity; the first
  // request can take ~30–60s to wake it. If startup is still pending after a
  // few seconds, surface a hint so the loading screen doesn't feel stuck.
  const [slowStart, setSlowStart] = useState(false)

  const authRequired = !!config?.auth_enabled
  const canUse = authReady && (!authRequired || !!user)

  useEffect(() => {
    captureTokenFromHash()
    getConfig()
      .then(async (cfg) => {
        setConfig(cfg)
        if (cfg.auth_enabled) {
          try {
            setUser(await getMe())
          } catch {
            setUser(null)
          }
        }
      })
      .catch(() => setConfig({ auth_enabled: false, auth_providers: [], llm_provider: '', supported_llm_providers: [] }))
      .finally(() => setAuthReady(true))
  }, [])

  // Reveal the "waking the server" hint if startup is still pending after 4s.
  useEffect(() => {
    if (authReady) return
    const timer = setTimeout(() => setSlowStart(true), 4000)
    return () => clearTimeout(timer)
  }, [authReady])

  // A 401 anywhere (expired token) drops the user back to the login screen.
  useEffect(() => {
    const onUnauthorized = () => setUser(null)
    window.addEventListener('auth:unauthorized', onUnauthorized)
    return () => window.removeEventListener('auth:unauthorized', onUnauthorized)
  }, [])

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions))
  }, [sessions])

  const refreshDocuments = useCallback(async () => {
    try {
      setDocuments(await listDocuments())
    } catch {
      setDocuments([])
    }
  }, [])

  useEffect(() => {
    if (canUse) refreshDocuments()
  }, [canUse, refreshDocuments])

  async function handleLogout() {
    await apiLogout()
    setUser(null)
    setDocuments([])
  }

  const active = sessions.find((s) => s.id === activeId) || sessions[0]

  // Accepts a functional updater applied against the latest session messages
  // inside setSessions, so rapid streaming updates never use a stale snapshot.
  function updateMessages(sessionId: string, updater: MessagesUpdater) {
    setSessions((prev) =>
      prev.map((s) =>
        s.id === sessionId
          ? {
              ...s,
              messages:
                typeof updater === 'function' ? updater(s.messages) : updater,
            }
          : s,
      ),
    )
  }

  function createSession() {
    const session = newSession(`Conversa ${sessions.length + 1}`)
    setSessions((prev) => [...prev, session])
    setActiveId(session.id)
    setSidebarOpen(false)
  }

  // Selecting a conversation also closes the mobile drawer.
  function selectSession(id: string) {
    setActiveId(id)
    setSidebarOpen(false)
  }

  function renameSession(id: string, name: string) {
    setSessions((prev) => prev.map((s) => (s.id === id ? { ...s, name } : s)))
  }

  function deleteSession(id: string) {
    setSessions((prev) => {
      const next = prev.filter((s) => s.id !== id)
      const safe = next.length ? next : [newSession('Conversa 1')]
      if (id === activeId) setActiveId(safe[0].id)
      return safe
    })
  }

  async function handleDeleteDocument(fileId: string) {
    await deleteDocument(fileId)
    refreshDocuments()
  }

  if (!authReady) {
    return (
      <div className="app-loading">
        <p>Carregando…</p>
        {slowStart && (
          <p className="app-loading-hint">
            Acordando o servidor… no primeiro acesso isso pode levar até 1 minuto.
          </p>
        )}
      </div>
    )
  }

  if (authRequired && !user) {
    return <LoginScreen providers={config?.auth_providers || []} />
  }

  return (
    <div className="app">
      {sidebarOpen && (
        <div className="overlay" onClick={() => setSidebarOpen(false)} />
      )}

      <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
        <div className="brand-row">
          <h1 className="brand">
            <span className="brand-dot" aria-hidden="true" />
            Chat com Documentos
          </h1>
          <button
            className="drawer-close"
            onClick={() => setSidebarOpen(false)}
            aria-label="Fechar menu"
          >
            ✕
          </button>
        </div>
        {authRequired && user && (
          <div className="user-bar">
            <span className="user-name" title={user.email}>
              {user.name}
            </span>
            <button className="logout-btn" onClick={handleLogout}>
              Sair
            </button>
          </div>
        )}
        <ApiKeyInput />
        <FileUpload onUploaded={refreshDocuments} />
        <section>
          <h3>Documentos</h3>
          <DocumentList documents={documents} onDelete={handleDeleteDocument} />
        </section>
        <SessionSidebar
          sessions={sessions}
          activeId={active.id}
          onSelect={selectSession}
          onCreate={createSession}
          onRename={renameSession}
          onDelete={deleteSession}
        />
      </aside>

      <main className="main">
        <header className="topbar">
          <button
            className="menu-btn"
            onClick={() => setSidebarOpen(true)}
            aria-label="Abrir menu"
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <line x1="3" y1="6" x2="21" y2="6" />
              <line x1="3" y1="12" x2="21" y2="12" />
              <line x1="3" y1="18" x2="21" y2="18" />
            </svg>
          </button>
          <h2>{active.name}</h2>
        </header>
        <ChatWindow session={active} onMessages={updateMessages} />
      </main>
    </div>
  )
}
