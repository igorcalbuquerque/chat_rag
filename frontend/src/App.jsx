import { useCallback, useEffect, useState } from 'react'
import ApiKeyInput from './components/ApiKeyInput'
import ChatWindow from './components/ChatWindow'
import DocumentList from './components/DocumentList'
import FileUpload from './components/FileUpload'
import SessionSidebar from './components/SessionSidebar'
import { deleteDocument, listDocuments } from './api/client'

const STORAGE_KEY = 'chat-rag-sessions'

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
    refreshDocuments()
  }, [refreshDocuments])

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

  return (
    <div className="app">
      <aside className="sidebar">
        <h1 className="brand">Chat com Documentos</h1>
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
