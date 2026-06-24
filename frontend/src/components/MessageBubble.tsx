import SourcesPanel from './SourcesPanel'
import type { ChatMessage } from '../types'

interface MessageBubbleProps {
  message: ChatMessage
}

// A single chat message (user or assistant). Assistant messages may carry the
// list of sources used to produce the answer.
export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user'
  return (
    <div className={`bubble-row ${isUser ? 'user' : 'assistant'}`}>
      <div className="bubble">
        <div className="bubble-content">
          {message.content ? (
            message.content
          ) : message.pending ? (
            <span className="typing" aria-label="Gerando resposta">
              <span />
              <span />
              <span />
            </span>
          ) : (
            ''
          )}
        </div>
        {!isUser && <SourcesPanel sources={message.sources} />}
      </div>
    </div>
  )
}
