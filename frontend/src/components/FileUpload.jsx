import { useRef, useState } from 'react'
import { uploadFiles } from '../api/client'

// Drag-and-drop + file picker with an ingestion progress indicator.
export default function FileUpload({ onUploaded }) {
  const inputRef = useRef(null)
  const [dragging, setDragging] = useState(false)
  const [progress, setProgress] = useState(null)
  const [error, setError] = useState(null)

  async function handleFiles(fileList) {
    const files = Array.from(fileList).filter((f) =>
      /\.(pdf|txt)$/i.test(f.name),
    )
    if (files.length === 0) {
      setError('Apenas arquivos PDF ou TXT são aceitos.')
      return
    }
    setError(null)
    setProgress(0)
    try {
      await uploadFiles(files, setProgress)
      setProgress(100)
      onUploaded?.()
    } catch (err) {
      setError('Falha no upload: ' + (err.message || 'erro desconhecido'))
    } finally {
      setTimeout(() => setProgress(null), 800)
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
        <small>PDF ou TXT</small>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.txt"
          multiple
          hidden
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>

      {progress !== null && (
        <div className="progress">
          <div className="progress-bar" style={{ width: `${progress}%` }} />
          <span>{progress < 100 ? `Indexando… ${progress}%` : 'Concluído'}</span>
        </div>
      )}
      {error && <p className="error">{error}</p>}
    </div>
  )
}
