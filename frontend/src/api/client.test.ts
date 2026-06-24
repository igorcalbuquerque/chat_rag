import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  API_KEY_STORAGE,
  AUTH_TOKEN_STORAGE,
  PROVIDER_STORAGE,
  getToken,
  loginUrl,
  setToken,
  streamChat,
} from './client'
import type { ChatResponse } from '../types'

// Build a minimal fetch Response whose body streams the given SSE string.
function sseResponse(sse: string, status = 200): Response {
  const chunks = [new TextEncoder().encode(sse)]
  let i = 0
  return {
    ok: status >= 200 && status < 300,
    status,
    body: {
      getReader: () => ({
        read: () =>
          i < chunks.length
            ? Promise.resolve({ value: chunks[i++], done: false })
            : Promise.resolve({ value: undefined, done: true }),
      }),
    },
  } as unknown as Response
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe('token helpers', () => {
  it('stores and reads the auth token', () => {
    expect(getToken()).toBe('')
    setToken('abc')
    expect(localStorage.getItem(AUTH_TOKEN_STORAGE)).toBe('abc')
    expect(getToken()).toBe('abc')
    setToken('')
    expect(getToken()).toBe('')
  })

  it('builds the OAuth login URL', () => {
    expect(loginUrl('google')).toBe('/api/auth/login/google')
  })
})

describe('streamChat', () => {
  it('parses SSE tokens and the final payload, sending auth headers', async () => {
    localStorage.setItem(API_KEY_STORAGE, 'sk-test')
    localStorage.setItem(PROVIDER_STORAGE, 'openai')
    setToken('tok-1')

    const sse =
      'event: token\ndata: {"token":"He"}\n\n' +
      'event: token\ndata: {"token":"llo"}\n\n' +
      'event: done\ndata: {"answer":"Hello","sources":[],"session_id":"s1"}\n\n'

    const fetchMock = vi.fn().mockResolvedValue(sseResponse(sse))
    vi.stubGlobal('fetch', fetchMock)

    const tokens: string[] = []
    let done: ChatResponse | undefined
    await streamChat(
      { question: 'hi', sessionId: 's1' },
      { onToken: (t) => tokens.push(t), onDone: (p) => (done = p) },
    )

    expect(tokens).toEqual(['He', 'llo'])
    expect(done?.answer).toBe('Hello')

    const [, init] = fetchMock.mock.calls[0]
    expect(init.headers['X-API-Key']).toBe('sk-test')
    expect(init.headers['X-LLM-Provider']).toBe('openai')
    expect(init.headers['Authorization']).toBe('Bearer tok-1')
    expect(JSON.parse(init.body)).toEqual({ question: 'hi', session_id: 's1', top_k: undefined })
  })

  it('on 401 clears the token, emits auth:unauthorized and calls onError', async () => {
    setToken('expired')
    const fetchMock = vi.fn().mockResolvedValue(sseResponse('', 401))
    vi.stubGlobal('fetch', fetchMock)

    const onUnauthorized = vi.fn()
    window.addEventListener('auth:unauthorized', onUnauthorized)
    const onError = vi.fn()

    await streamChat({ question: 'hi', sessionId: 's1' }, { onError })

    expect(onUnauthorized).toHaveBeenCalled()
    expect(getToken()).toBe('')
    expect(onError).toHaveBeenCalled()
    window.removeEventListener('auth:unauthorized', onUnauthorized)
  })

  it('routes a thrown fetch error to onError', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('network down')))
    const onError = vi.fn()
    await streamChat({ question: 'hi', sessionId: 's1' }, { onError })
    expect(onError).toHaveBeenCalledOnce()
  })
})
