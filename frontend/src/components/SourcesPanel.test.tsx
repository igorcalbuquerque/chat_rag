import { describe, expect, it } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import SourcesPanel from './SourcesPanel'
import type { Source } from '../types'

const sources: Source[] = [
  { chunk: 'first chunk text', source: 'a.pdf', score: 0.91 },
  { chunk: 'second chunk text', source: 'b.txt', score: 0.72 },
]

describe('SourcesPanel', () => {
  it('renders nothing when there are no sources', () => {
    const { container } = render(<SourcesPanel sources={[]} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('shows the source count and toggles the list open/closed', () => {
    render(<SourcesPanel sources={sources} />)
    const toggle = screen.getByRole('button', { name: /fontes \(2\)/i })

    // Collapsed initially.
    expect(screen.queryByText('first chunk text')).not.toBeInTheDocument()

    fireEvent.click(toggle)
    expect(screen.getByText('first chunk text')).toBeInTheDocument()
    expect(screen.getByText('a.pdf')).toBeInTheDocument()
    expect(screen.getByText('score 0.91')).toBeInTheDocument()

    fireEvent.click(toggle)
    expect(screen.queryByText('first chunk text')).not.toBeInTheDocument()
  })
})
