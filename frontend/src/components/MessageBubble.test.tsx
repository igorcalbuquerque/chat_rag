import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import MessageBubble from './MessageBubble'
import type { ChatMessage } from '../types'

describe('MessageBubble', () => {
  it('renders a user message without a sources panel', () => {
    const message: ChatMessage = { role: 'user', content: 'Hello there' }
    render(<MessageBubble message={message} />)
    expect(screen.getByText('Hello there')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /fontes/i })).not.toBeInTheDocument()
  })

  it('shows the typing indicator while an assistant message is pending', () => {
    const message: ChatMessage = { role: 'assistant', content: '', pending: true }
    render(<MessageBubble message={message} />)
    expect(screen.getByLabelText('Gerando resposta')).toBeInTheDocument()
  })

  it('renders the sources panel for an assistant answer with sources', () => {
    const message: ChatMessage = {
      role: 'assistant',
      content: 'The answer',
      sources: [{ chunk: 'c', source: 's.pdf', score: 0.5 }],
    }
    render(<MessageBubble message={message} />)
    expect(screen.getByText('The answer')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /fontes \(1\)/i })).toBeInTheDocument()
  })
})
