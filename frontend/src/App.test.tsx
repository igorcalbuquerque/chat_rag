import { describe, expect, it, vi } from 'vitest'
import { act, render, screen, waitFor } from '@testing-library/react'
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
    // Documents are loaded by an effect that runs after the commit, so retry.
    await waitFor(() => expect(listDocuments).toHaveBeenCalled())
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

  it('shows the "waking the server" hint after a few seconds of loading', () => {
    vi.useFakeTimers()
    // Keep startup pending so the loading screen stays up.
    vi.mocked(getConfig).mockReturnValue(new Promise(() => {}))

    try {
      render(<App />)

      // Loading immediately, hint not yet.
      expect(screen.getByText(/carregando/i)).toBeInTheDocument()
      expect(screen.queryByText(/acordando o servidor/i)).not.toBeInTheDocument()

      // After the delay, the hint appears.
      act(() => {
        vi.advanceTimersByTime(4000)
      })
      expect(screen.getByText(/acordando o servidor/i)).toBeInTheDocument()
    } finally {
      vi.useRealTimers()
    }
  })
})
