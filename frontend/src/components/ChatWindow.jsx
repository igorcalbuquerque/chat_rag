import { useEffect, useRef, useState } from 'react'
import { streamChat } from '../api/client'
import MessageBubble from './MessageBubble'

// Chat history + input. Sends questions with streaming so the answer appears
// token by token. Enter submits; Shift+Enter inserts a newline.
export default function ChatWindow({ session, onMessages }) {
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const scrollRef = useRef(null)
  const messages = session.messages

  useEffect(() => {
    scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight)
  }, [messages])

  // Forward the updater straight through to App, pinning the session id so
  // streaming writes always land in the right conversation.
  function setMessages(updater) {
    onMessages(session.id, updater)
  }

  async function handleSend() {
    const question = input.trim()
    if (!question || busy) return
    setInput('')
    setBusy(true)

    const userMsg = { role: 'user', content: question }
    const assistantMsg = { role: 'assistant', content: '', sources: [], pending: true }
    setMessages((prev) => [...prev, userMsg, assistantMsg])

    await streamChat(
      { question, sessionId: session.id },
      {
        onToken: (token) =>
          setMessages((prev) => {
            const next = [...prev]
            const last = next[next.length - 1]
            next[next.length - 1] = { ...last, content: last.content + token }
            return next
          }),
        onDone: (payload) =>
          setMessages((prev) => {
            const next = [...prev]
            next[next.length - 1] = {
              role: 'assistant',
              content: payload.answer,
              sources: payload.sources,
              pending: false,
            }
            return next
          }),
        onError: () =>
          setMessages((prev) => {
            const next = [...prev]
            next[next.length - 1] = {
              role: 'assistant',
              content: '⚠️ Erro ao gerar a resposta.',
              sources: [],
              pending: false,
            }
            return next
          }),
      },
    )
    setBusy(false)
  }

  return (
    <div className="chat">
      <div className="messages" ref={scrollRef}>
        {messages.length === 0 && (
          <p className="muted center">
            Faça uma pergunta sobre os documentos enviados.
          </p>
        )}
        {messages.map((m, i) => (
          <MessageBubble key={i} message={m} />
        ))}
        {busy && <p className="muted center small">assistente digitando…</p>}
      </div>

      <div className="composer">
        <textarea
          value={input}
          placeholder="Digite sua pergunta…"
          rows={1}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              handleSend()
            }
          }}
        />
        <button onClick={handleSend} disabled={busy || !input.trim()}>
          Enviar
        </button>
      </div>
    </div>
  )
}
