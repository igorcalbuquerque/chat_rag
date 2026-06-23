import { useRef, useState } from 'react'
import { uploadFiles } from '../api/client'

// Turn an Axios/HTTP error into a human message, preferring the backend detail.
function describeError(err) {
  if (err?.response?.status === 413) {
    return 'Arquivo muito grande para upload.'
  }
  const detail = err?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map((d) => d.msg).join('; ')
  return err?.message || 'erro desconhecido'
}

// Drag-and-drop + file picker. Reports two distinct phases — "uploading"
// (bytes sent) and "processing" (server-side ingestion) — and surfaces the
// real backend error if ingestion fails.
export default function FileUpload({ onUploaded }) {
  const inputRef = useRef(null)
  const [dragging, setDragging] = useState(false)
  const [status, setStatus] = useState(null) // {phase, pct?}
  const [error, setError] = useState(null)

  async function handleFiles(fileList) {
    const files = Array.from(fileList).filter((f) =>
      /\.(pdf|txt|docx)$/i.test(f.name),
    )
    if (files.length === 0) {
      setError('Apenas arquivos PDF, TXT ou DOCX são aceitos.')
      return
    }
    setError(null)
    setStatus({ phase: 'uploading', pct: 0 })
    try {
      // Once all bytes are sent, the server is still ingesting -> "processing".
      const data = await uploadFiles(files, (pct) =>
        setStatus(pct < 100 ? { phase: 'uploading', pct } : { phase: 'processing' }),
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
      setError('Falha no upload: ' + describeError(err))
    } finally {
      setTimeout(() => setStatus(null), 1500)
    }
  }

  return (
    <div className="upload">
      <div
        className={`dropzone ${dragging ? 'dragging' : ''}`}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragging(false)
          handleFiles(e.dataTransfer.files)
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
              <span>Enviando… {status.pct}%</span>
            </>
          )}
          {status.phase === 'processing' && (
            <>
              <div className="progress-track">
                <div className="progress-bar indeterminate" />
              </div>
              <span>Processando e indexando…</span>
            </>
          )}
          {status.phase === 'done' && <span className="ok">✓ Indexado</span>}
        </div>
      )}
      {error && <p className="error">{error}</p>}
    </div>
  )
}
