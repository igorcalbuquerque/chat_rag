import { useEffect, useRef, useState } from 'react'
import { streamChat } from '../api/client'
import MessageBubble from './MessageBubble'
import type { ChatMessage, Session } from '../types'

type MessagesUpdater = ChatMessage[] | ((prev: ChatMessage[]) => ChatMessage[])

interface ChatWindowProps {
  session: Session
  onMessages: (sessionId: string, updater: MessagesUpdater) => void
}

// Chat history + input. Sends questions with streaming so the answer appears
// token by token. Enter submits; Shift+Enter inserts a newline.
export default function ChatWindow({ session, onMessages }: ChatWindowProps) {
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)
  const messages = session.messages

  useEffect(() => {
    scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight)
  }, [messages])

  // Forward the updater straight through to App, pinning the session id so
  // streaming writes always land in the right conversation.
  function setMessages(updater: MessagesUpdater) {
    onMessages(session.id, updater)
  }

  async function handleSend() {
    const question = input.trim()
    if (!question || busy) return
    setInput('')
    setBusy(true)

    const userMsg: ChatMessage = { role: 'user', content: question }
    const assistantMsg: ChatMessage = { role: 'assistant', content: '', sources: [], pending: true }
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
          <div className="onboarding">
            <div className="ob-icon">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
              </svg>
            </div>
            <div>
              <h2>Converse com seus documentos</h2>
              <p>
                Envie um arquivo e pergunte qualquer coisa sobre ele — as
                respostas vêm com as fontes usadas.
              </p>
            </div>
            <div className="ob-steps">
              <div className="ob-step">
                <span className="ob-num">1</span>
                <span>Envie um PDF, DOCX ou TXT para indexar</span>
              </div>
              <div className="ob-step">
                <span className="ob-num">2</span>
                <span>Faça sua pergunta aqui embaixo</span>
              </div>
            </div>
          </div>
        )}
        {messages.map((m, i) => (
          <MessageBubble key={i} message={m} />
        ))}
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
        <button
          className="send-btn"
          onClick={handleSend}
          disabled={busy || !input.trim()}
          aria-label="Enviar"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="12" y1="19" x2="12" y2="5" />
            <polyline points="5 12 12 5 19 12" />
          </svg>
        </button>
      </div>
    </div>
  )
}
