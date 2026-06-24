import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import App from './App'
import { getConfig, getMe, listDocuments } from './api/client'
import type { AppConfig } from './types'

// App pulls in the whole component tree; mock the client so no real HTTP runs.
vi.mock('./api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./api/client')>()
  return {
    ...actual,
    getConfig: vi.fn(),
    getMe: vi.fn(),
    listDocuments: vi.fn().mockResolvedValue([]),
    deleteDocument: vi.fn(),
    uploadFiles: vi.fn(),
    streamChat: vi.fn(),
    logout: vi.fn(),
  }
})

const baseConfig: AppConfig = {
  llm_provider: 'ollama',
  supported_llm_providers: ['ollama', 'openai'],
  auth_enabled: false,
  auth_providers: [],
}

describe('App', () => {
  it('renders the main UI when auth is disabled', async () => {
    vi.mocked(getConfig).mockResolvedValue(baseConfig)

    render(<App />)

    await waitFor(() =>
      expect(screen.getByText(/converse com seus documentos/i)).toBeInTheDocument(),
    )
    // Sidebar brand + active session title are present.
    expect(screen.getAllByText(/chat com documentos/i).length).toBeGreaterThan(0)
    expect(listDocuments).toHaveBeenCalled()
  })

  it('shows the login screen when auth is required and there is no user', async () => {
    vi.mocked(getConfig).mockResolvedValue({
      ...baseConfig,
      auth_enabled: true,
      auth_providers: ['google', 'github'],
    })
    vi.mocked(getMe).mockRejectedValue(new Error('401'))

    render(<App />)

    await waitFor(() =>
      expect(screen.getByText(/entrar com google/i)).toBeInTheDocument(),
    )
    expect(screen.getByText(/entrar com github/i)).toBeInTheDocument()
  })
})
