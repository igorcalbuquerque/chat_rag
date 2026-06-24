import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import FileUpload from './FileUpload'
import { uploadFiles } from '../api/client'

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>()
  return { ...actual, uploadFiles: vi.fn() }
})

function pickFiles(files: File[]) {
  const input = document.querySelector('input[type="file"]') as HTMLInputElement
  fireEvent.change(input, { target: { files } })
}

beforeEach(() => {
  vi.mocked(uploadFiles).mockReset()
})

describe('FileUpload', () => {
  it('rejects unsupported file types', () => {
    render(<FileUpload />)
    pickFiles([new File(['x'], 'image.png', { type: 'image/png' })])
    expect(screen.getByText(/apenas arquivos pdf, txt ou docx/i)).toBeInTheDocument()
    expect(uploadFiles).not.toHaveBeenCalled()
  })

  it('uploads a supported file and notifies the parent', async () => {
    vi.mocked(uploadFiles).mockResolvedValue({
      files: [{ file_id: 'f1', name: 'doc.txt', chunks_indexed: 2 }],
    })
    const onUploaded = vi.fn()
    render(<FileUpload onUploaded={onUploaded} />)

    pickFiles([new File(['hello'], 'doc.txt', { type: 'text/plain' })])

    await waitFor(() => expect(onUploaded).toHaveBeenCalledOnce())
    expect(uploadFiles).toHaveBeenCalledOnce()
  })

  it('surfaces an error when nothing was extracted', async () => {
    vi.mocked(uploadFiles).mockResolvedValue({
      files: [{ file_id: 'f1', name: 'scan.pdf', chunks_indexed: 0 }],
    })
    render(<FileUpload />)

    pickFiles([new File(['x'], 'scan.pdf', { type: 'application/pdf' })])

    await waitFor(() =>
      expect(screen.getByText(/nenhum texto foi extraído/i)).toBeInTheDocument(),
    )
  })
})
