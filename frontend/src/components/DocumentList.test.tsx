import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import DocumentList from './DocumentList'
import type { DocumentItem } from '../types'

const docs: DocumentItem[] = [
  { file_id: 'f1', name: 'report.pdf', chunks: 3 },
  { file_id: 'f2', name: 'notes.txt', chunks: 1 },
]

describe('DocumentList', () => {
  it('shows an empty-state message when there are no documents', () => {
    render(<DocumentList documents={[]} onDelete={() => {}} />)
    expect(screen.getByText(/nenhum documento indexado/i)).toBeInTheDocument()
  })

  it('renders each document with its chunk count', () => {
    render(<DocumentList documents={docs} onDelete={() => {}} />)
    expect(screen.getByText('report.pdf')).toBeInTheDocument()
    expect(screen.getByText('3 chunks')).toBeInTheDocument()
    expect(screen.getByText('notes.txt')).toBeInTheDocument()
  })

  it('calls onDelete with the file_id when the remove button is clicked', () => {
    const onDelete = vi.fn()
    render(<DocumentList documents={docs} onDelete={onDelete} />)
    fireEvent.click(screen.getAllByTitle('Remover documento')[0])
    expect(onDelete).toHaveBeenCalledWith('f1')
  })
})
