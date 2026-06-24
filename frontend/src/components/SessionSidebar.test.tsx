import { afterEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import SessionSidebar from './SessionSidebar'
import type { Session } from '../types'

const sessions: Session[] = [
  { id: 's1', name: 'Conversa 1', messages: [] },
  { id: 's2', name: 'Conversa 2', messages: [] },
]

function setup(overrides = {}) {
  const handlers = {
    onSelect: vi.fn(),
    onCreate: vi.fn(),
    onRename: vi.fn(),
    onDelete: vi.fn(),
    ...overrides,
  }
  render(<SessionSidebar sessions={sessions} activeId="s1" {...handlers} />)
  return handlers
}

afterEach(() => vi.restoreAllMocks())

describe('SessionSidebar', () => {
  it('marks the active session', () => {
    setup()
    expect(screen.getByText('Conversa 1').closest('li')).toHaveClass('active')
    expect(screen.getByText('Conversa 2').closest('li')).not.toHaveClass('active')
  })

  it('creates a new session', () => {
    const { onCreate } = setup()
    fireEvent.click(screen.getByTitle('Nova conversa'))
    expect(onCreate).toHaveBeenCalledOnce()
  })

  it('selects a session on click', () => {
    const { onSelect } = setup()
    fireEvent.click(screen.getByText('Conversa 2'))
    expect(onSelect).toHaveBeenCalledWith('s2')
  })

  it('deletes a session without selecting it (stopPropagation)', () => {
    const { onDelete, onSelect } = setup()
    fireEvent.click(screen.getAllByTitle('Excluir conversa')[1])
    expect(onDelete).toHaveBeenCalledWith('s2')
    expect(onSelect).not.toHaveBeenCalled()
  })

  it('renames via the prompt dialog on double-click', () => {
    vi.spyOn(window, 'prompt').mockReturnValue('Renamed')
    const { onRename } = setup()
    fireEvent.doubleClick(screen.getByText('Conversa 1'))
    expect(onRename).toHaveBeenCalledWith('s1', 'Renamed')
  })

  it('does not rename when the prompt is cancelled', () => {
    vi.spyOn(window, 'prompt').mockReturnValue(null)
    const { onRename } = setup()
    fireEvent.doubleClick(screen.getByText('Conversa 1'))
    expect(onRename).not.toHaveBeenCalled()
  })
})
