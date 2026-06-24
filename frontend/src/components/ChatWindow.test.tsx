import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import ChatWindow from './ChatWindow'
import { streamChat } from '../api/client'
import type { ChatMessage, Session } from '../types'

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>()
  return { ...actual, streamChat: vi.fn() }
})

// A tiny stateful host that mirrors App's updateMessages contract, so the
// component under test actually re-renders with the streamed messages.
function Host({ initial = [] as ChatMessage[] }) {
  const session: Session = { id: 's1', name: 'Conversa 1', messages: initial }
  let messages = initial
  function onMessages(
    _id: string,
    updater: ChatMessage[] | ((prev: ChatMessage[]) => ChatMessage[]),
  ) {
    messages = typeof updater === 'function' ? updater(messages) : updater
    session.messages = messages
  }
  return <ChatWindow session={session} onMessages={onMessages} />
}

describe('ChatWindow', () => {
  it('renders the onboarding hint when there are no messages', () => {
    render(<Host />)
    expect(screen.getByText(/converse com seus documentos/i)).toBeInTheDocument()
  })

  it('sends the question on Enter and renders the streamed answer', async () => {
    vi.mocked(streamChat).mockImplementation(async (_params, handlers) => {
      handlers.onToken?.('Hel')
      handlers.onToken?.('lo')
      handlers.onDone?.({ answer: 'Hello', sources: [], session_id: 's1' })
    })

    render(<Host />)
    const textarea = screen.getByPlaceholderText(/digite sua pergunta/i)
    fireEvent.change(textarea, { target: { value: 'Hi?' } })
    fireEvent.keyDown(textarea, { key: 'Enter' })

    await waitFor(() => expect(streamChat).toHaveBeenCalledOnce())
    expect(screen.getByText('Hi?')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByText('Hello')).toBeInTheDocument())
  })

  it('does not send on empty input', () => {
    render(<Host />)
    const textarea = screen.getByPlaceholderText(/digite sua pergunta/i)
    fireEvent.keyDown(textarea, { key: 'Enter' })
    expect(streamChat).not.toHaveBeenCalled()
  })

  it('shows an error message when streaming fails', async () => {
    vi.mocked(streamChat).mockImplementation(async (_params, handlers) => {
      handlers.onError?.(new Error('boom'))
    })
    render(<Host />)
    const textarea = screen.getByPlaceholderText(/digite sua pergunta/i)
    fireEvent.change(textarea, { target: { value: 'Hi?' } })
    fireEvent.keyDown(textarea, { key: 'Enter' })
    await waitFor(() =>
      expect(screen.getByText(/erro ao gerar a resposta/i)).toBeInTheDocument(),
    )
  })
})
