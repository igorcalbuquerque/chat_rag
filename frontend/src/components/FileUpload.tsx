import { useRef, useState } from 'react'
import { uploadFiles } from '../api/client'

interface FileUploadProps {
  onUploaded?: () => void
}

type UploadStatus =
  | { phase: 'uploading'; pct: number }
  | { phase: 'processing' }
  | { phase: 'done' }
  | null

// Shape we read off an Axios/HTTP error without depending on Axios types here.
interface HttpErrorLike {
  response?: { status?: number; data?: { detail?: unknown } }
  message?: string
  code?: string
  name?: string
}

// Turn an Axios/HTTP error into a human message, preferring the backend detail.
function describeError(err: unknown): string {
  const e = err as HttpErrorLike
  if (e?.response?.status === 413) {
    return 'Arquivo muito grande para upload.'
  }
  const detail = e?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map((d) => d.msg).join('; ')
  return e?.message || 'erro desconhecido'
}

// Drag-and-drop + file picker. Reports two distinct phases — "uploading"
// (bytes sent) and "processing" (server-side ingestion) — and surfaces the
// real backend error if ingestion fails.
export default function FileUpload({ onUploaded }: FileUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const abortRef = useRef<AbortController | null>(null)
  const [dragging, setDragging] = useState(false)
  const [status, setStatus] = useState<UploadStatus>(null)
  const [error, setError] = useState<string | null>(null)
  const [note, setNote] = useState<string | null>(null)

  const busy = status?.phase === 'uploading' || status?.phase === 'processing'

  function cancelUpload() {
    abortRef.current?.abort()
  }

  async function handleFiles(fileList: FileList | null) {
    if (busy || !fileList) return // one upload at a time
    const files = Array.from(fileList).filter((f) => /\.(pdf|txt|docx)$/i.test(f.name))
    if (files.length === 0) {
      setError('Apenas arquivos PDF, TXT ou DOCX são aceitos.')
      return
    }
    setError(null)
    setNote(null)
    setStatus({ phase: 'uploading', pct: 0 })

    const controller = new AbortController()
    abortRef.current = controller
    try {
      // Once all bytes are sent, the server is still ingesting -> "processing".
      const data = await uploadFiles(
        files,
        (pct) =>
          setStatus(pct < 100 ? { phase: 'uploading', pct } : { phase: 'processing' }),
        controller.signal,
      )

      const indexed = (data.files || []).reduce(
        (sum, f) => sum + (f.chunks_indexed || 0),
        0,
      )
      if (indexed === 0) {
        setStatus(null)
        setError('Nenhum texto foi extraído (PDF escaneado/imagem?).')
        return
      }
      setStatus({ phase: 'done' })
      onUploaded?.()
    } catch (err) {
      setStatus(null)
      const e = err as HttpErrorLike
      if (e?.code === 'ERR_CANCELED' || e?.name === 'CanceledError') {
        setNote('Envio cancelado.')
      } else {
        setError('Falha no upload: ' + describeError(err))
      }
    } finally {
      abortRef.current = null
      setTimeout(() => setStatus(null), 1500)
    }
  }

  return (
    <div className="upload">
      <div
        className={`dropzone ${dragging ? 'dragging' : ''} ${busy ? 'disabled' : ''}`}
        onClick={() => !busy && inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault()
          if (!busy) setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragging(false)
          if (!busy) handleFiles(e.dataTransfer.files)
        }}
      >
        <p>📄 Arraste arquivos aqui ou clique para selecionar</p>
        <small>PDF, TXT ou DOCX</small>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.txt,.docx"
          multiple
          hidden
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>

      {status && (
        <div className="progress">
          {status.phase === 'uploading' && (
            <>
              <div className="progress-track">
                <div className="progress-bar" style={{ width: `${status.pct}%` }} />
              </div>
              <div className="progress-row">
                <span>Enviando… {status.pct}%</span>
                <button type="button" className="cancel-btn" onClick={cancelUpload}>
                  Cancelar
                </button>
              </div>
            </>
          )}
          {status.phase === 'processing' && (
            <>
              <div className="progress-track">
                <div className="progress-bar indeterminate" />
              </div>
              <div className="progress-row">
                <span>Processando e indexando…</span>
                <button type="button" className="cancel-btn" onClick={cancelUpload}>
                  Cancelar
                </button>
              </div>
            </>
          )}
          {status.phase === 'done' && <span className="ok">✓ Indexado</span>}
        </div>
      )}
      {note && <p className="muted">{note}</p>}
      {error && <p className="error">{error}</p>}
    </div>
  )
}
