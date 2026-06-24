import type { DocumentItem } from '../types'

interface DocumentListProps {
  documents: DocumentItem[]
  onDelete: (fileId: string) => void
}

// List of indexed documents with a remove button per document.
export default function DocumentList({ documents, onDelete }: DocumentListProps) {
  if (!documents.length) {
    return <p className="muted">Nenhum documento indexado ainda.</p>
  }

  return (
    <ul className="doc-list">
      {documents.map((doc) => (
        <li key={doc.file_id} className="doc-item">
          <div className="doc-meta">
            <span className="doc-name" title={doc.name}>
              {doc.name}
            </span>
            <small>{doc.chunks} chunks</small>
          </div>
          <button
            className="icon-btn"
            title="Remover documento"
            onClick={() => onDelete(doc.file_id)}
          >
            ✕
          </button>
        </li>
      ))}
    </ul>
  )
}
