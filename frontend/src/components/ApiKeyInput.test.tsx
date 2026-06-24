import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import ApiKeyInput from './ApiKeyInput'
import { API_KEY_STORAGE, PROVIDER_STORAGE, getConfig } from '../api/client'
import type { AppConfig } from '../types'

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>()
  return { ...actual, getConfig: vi.fn() }
})

const config: AppConfig = {
  llm_provider: 'openai',
  supported_llm_providers: ['openai', 'ollama'],
  auth_enabled: false,
  auth_providers: [],
}

beforeEach(() => {
  vi.mocked(getConfig).mockResolvedValue(config)
})

describe('ApiKeyInput', () => {
  it('defaults to the server provider and shows a key field for OpenAI', async () => {
    render(<ApiKeyInput />)
    await waitFor(() => expect(screen.getByLabelText(/chave de api/i)).toBeInTheDocument())
    expect(screen.getByRole('combobox')).toHaveValue('openai')
  })

  it('persists the chosen provider and hides the key field for a local provider', async () => {
    render(<ApiKeyInput />)
    await waitFor(() => expect(screen.getByRole('combobox')).toHaveValue('openai'))

    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'ollama' } })

    expect(localStorage.getItem(PROVIDER_STORAGE)).toBe('ollama')
    expect(screen.queryByLabelText(/chave de api/i)).not.toBeInTheDocument()
    expect(screen.getByText(/não precisa de chave/i)).toBeInTheDocument()
  })

  it('saves the typed API key to localStorage', async () => {
    render(<ApiKeyInput />)
    const input = await screen.findByLabelText(/chave de api/i)
    fireEvent.change(input, { target: { value: 'sk-secret' } })
    expect(localStorage.getItem(API_KEY_STORAGE)).toBe('sk-secret')
  })
})
