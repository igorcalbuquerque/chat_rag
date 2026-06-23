import SourcesPanel from './SourcesPanel'

// A single chat message (user or assistant). Assistant messages may carry the
// list of sources used to produce the answer.
export default function MessageBubble({ message }) {
  const isUser = message.role === 'user'
  return (
    <div className={`bubble-row ${isUser ? 'user' : 'assistant'}`}>
      <div className="bubble">
        <div className="bubble-content">
          {message.content || (message.pending ? '▍' : '')}
        </div>
        {!isUser && <SourcesPanel sources={message.sources} />}
      </div>
    </div>
  )
}
