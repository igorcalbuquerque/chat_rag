import type { Session } from '../types'

interface SessionSidebarProps {
  sessions: Session[]
  activeId: string
  onSelect: (id: string) => void
  onCreate: () => void
  onRename: (id: string, name: string) => void
  onDelete: (id: string) => void
}

// Sidebar listing chat sessions, with create / rename / delete actions.
export default function SessionSidebar({
  sessions,
  activeId,
  onSelect,
  onCreate,
  onRename,
  onDelete,
}: SessionSidebarProps) {
  return (
    <div className="sessions">
      <div className="sessions-head">
        <h3>Conversas</h3>
        <button className="icon-btn" title="Nova conversa" onClick={onCreate}>
          ＋
        </button>
      </div>
      <ul>
        {sessions.map((s) => (
          <li
            key={s.id}
            className={s.id === activeId ? 'active' : ''}
            onClick={() => onSelect(s.id)}
          >
            <span
              className="session-name"
              onDoubleClick={() => {
                const name = prompt('Renomear conversa:', s.name)
                if (name) onRename(s.id, name)
              }}
            >
              {s.name}
            </span>
            <button
              className="icon-btn"
              title="Excluir conversa"
              onClick={(e) => {
                e.stopPropagation()
                onDelete(s.id)
              }}
            >
              ✕
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
