import type { DocumentItem } from '../types'

interface DocumentListProps {
  documents: DocumentItem[]
  onDelete: (fileId: string) => void
  loading?: boolean
}

function Loading({ label }: { label: string }) {
  return (
    <p className="muted doc-loading" role="status" aria-live="polite">
      <span className="doc-spinner" aria-hidden="true" />
      {label}
    </p>
  )
}

// List of indexed documents with a remove button per document. While the list
// is being (re)fetched a loading indicator is shown so a slow response (e.g. a
// remote Redis in production) never looks like an empty list or an error.
export default function DocumentList({ documents, onDelete, loading }: DocumentListProps) {
  // First load / nothing cached yet: show only the spinner.
  if (loading && !documents.length) {
    return <Loading label="Carregando documentos…" />
  }

  if (!documents.length) {
    return <p className="muted">Nenhum documento indexado ainda.</p>
  }

  return (
    <>
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
      {/* Refreshing with a list already shown (e.g. right after an upload). */}
      {loading && <Loading label="Atualizando…" />}
    </>
  )
}
