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

const STORAGE_KEY = 'chat-rag-sessions'

// If the OAuth callback returned a token in the URL fragment, persist it and
// clean the URL so it doesn't linger in history.
function captureTokenFromHash() {
  const hash = window.location.hash
  if (hash.startsWith('#token=')) {
    setToken(decodeURIComponent(hash.slice('#token='.length)))
    window.history.replaceState(null, '', window.location.pathname + window.location.search)
  }
}

function loadSessions() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) return JSON.parse(raw)
  } catch {
    /* ignore corrupted storage */
  }
  return null
}

function newSession(name) {
  return { id: crypto.randomUUID(), name, messages: [] }
}

export default function App() {
  const [sessions, setSessions] = useState(
    () => loadSessions() || [newSession('Conversa 1')],
  )
  const [activeId, setActiveId] = useState(() => sessions[0].id)
  const [documents, setDocuments] = useState([])

  // Auth state. config === null while loading. When auth is disabled the app
  // is open; when enabled, `user` must be set (valid token) to use the app.
  const [config, setConfig] = useState(null)
  const [user, setUser] = useState(null)
  const [authReady, setAuthReady] = useState(false)

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
      .catch(() => setConfig({ auth_enabled: false, auth_providers: [] }))
      .finally(() => setAuthReady(true))
  }, [])

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
  function updateMessages(sessionId, updater) {
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
  }

  function renameSession(id, name) {
    setSessions((prev) => prev.map((s) => (s.id === id ? { ...s, name } : s)))
  }

  function deleteSession(id) {
    setSessions((prev) => {
      const next = prev.filter((s) => s.id !== id)
      const safe = next.length ? next : [newSession('Conversa 1')]
      if (id === activeId) setActiveId(safe[0].id)
      return safe
    })
  }

  async function handleDeleteDocument(fileId) {
    await deleteDocument(fileId)
    refreshDocuments()
  }

  if (!authReady) {
    return <div className="app-loading">Carregando…</div>
  }

  if (authRequired && !user) {
    return <LoginScreen providers={config.auth_providers || []} />
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <h1 className="brand">Chat com Documentos</h1>
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
          onSelect={setActiveId}
          onCreate={createSession}
          onRename={renameSession}
          onDelete={deleteSession}
        />
      </aside>

      <main className="main">
        <header className="topbar">
          <h2>{active.name}</h2>
        </header>
        <ChatWindow session={active} onMessages={updateMessages} />
      </main>
    </div>
  )
}
