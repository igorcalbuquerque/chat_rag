import { useEffect, useState } from 'react'
import { API_KEY_STORAGE, PROVIDER_STORAGE, getConfig } from '../api/client'

const LABELS = {
  openai: 'OpenAI',
  anthropic: 'Anthropic',
  gemini: 'Google Gemini',
  ollama: 'Ollama (local)',
}
// Providers that need an API key (mirrors the backend KEY_PROVIDERS).
const NEEDS_KEY = new Set(['openai', 'anthropic', 'gemini'])

// Lets the visitor pick the chat LLM provider and paste its key (sent per
// request as X-LLM-Provider / X-API-Key). Embeddings stay fixed on the server
// (the vector index dimension is per model), so only the chat model varies.
export default function ApiKeyInput() {
  const [config, setConfig] = useState(null)
  const [provider, setProvider] = useState(
    () => localStorage.getItem(PROVIDER_STORAGE) || '',
  )
  const [key, setKey] = useState(
    () => localStorage.getItem(API_KEY_STORAGE) || '',
  )

  useEffect(() => {
    getConfig()
      .then((cfg) => {
        setConfig(cfg)
        // Default the selector to the server's provider if the user hasn't picked.
        setProvider((p) => p || cfg.llm_provider)
      })
      .catch(() => setConfig(null))
  }, [])

  function persistProvider(next) {
    setProvider(next)
    localStorage.setItem(PROVIDER_STORAGE, next)
  }

  function persistKey(next) {
    setKey(next)
    if (next) localStorage.setItem(API_KEY_STORAGE, next)
    else localStorage.removeItem(API_KEY_STORAGE)
  }

  const options = config?.supported_llm_providers || []
  const needsKey = NEEDS_KEY.has(provider)

  return (
    <div className="apikey">
      <h3>Modelo de chat</h3>

      <label className="apikey-label">Provedor</label>
      <select value={provider} onChange={(e) => persistProvider(e.target.value)}>
        {options.length === 0 && <option value="">—</option>}
        {options.map((p) => (
          <option key={p} value={p}>
            {LABELS[p] || p}
          </option>
        ))}
      </select>

      {needsKey ? (
        <>
          <label className="apikey-label">Chave de API ({LABELS[provider]})</label>
          <input
            type="password"
            placeholder={`Cole sua chave ${LABELS[provider]}`}
            value={key}
            onChange={(e) => persistKey(e.target.value.trim())}
            autoComplete="off"
          />
          <small className="muted">
            Guardada só no seu navegador e enviada por requisição. Se vazia, o
            servidor usa a própria chave (.env).
          </small>
        </>
      ) : (
        <small className="muted">
          Provedor local — não precisa de chave.
        </small>
      )}
    </div>
  )
}
