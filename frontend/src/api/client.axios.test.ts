import { beforeEach, describe, expect, it, vi } from 'vitest'

// Mock the axios instance used by the client so we can assert how each helper
// calls the HTTP layer (routes, payloads, auth headers) without real requests.
const { instance } = vi.hoisted(() => ({
  instance: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
    interceptors: { response: { use: vi.fn() } },
  },
}))

vi.mock('axios', () => ({
  default: { create: vi.fn(() => instance) },
}))

import {
  API_KEY_STORAGE,
  AUTH_TOKEN_STORAGE,
  PROVIDER_STORAGE,
  deleteDocument,
  getConfig,
  getMe,
  listDocuments,
  logout,
  sendChat,
  uploadFiles,
} from './client'

beforeEach(() => {
  instance.get.mockReset()
  instance.post.mockReset()
  instance.delete.mockReset()
})

describe('client HTTP helpers', () => {
  it('getConfig hits /config and returns the data', async () => {
    instance.get.mockResolvedValue({ data: { llm_provider: 'openai' } })
    const cfg = await getConfig()
    expect(instance.get).toHaveBeenCalledWith('/config')
    expect(cfg).toEqual({ llm_provider: 'openai' })
  })

  it('listDocuments sends auth headers from localStorage', async () => {
    localStorage.setItem(AUTH_TOKEN_STORAGE, 'tok')
    localStorage.setItem(API_KEY_STORAGE, 'sk')
    localStorage.setItem(PROVIDER_STORAGE, 'openai')
    instance.get.mockResolvedValue({ data: [] })

    await listDocuments()

    const [route, opts] = instance.get.mock.calls[0]
    expect(route).toBe('/documents')
    expect(opts.headers).toMatchObject({
      Authorization: 'Bearer tok',
      'X-API-Key': 'sk',
      'X-LLM-Provider': 'openai',
    })
  })

  it('deleteDocument targets the document id', async () => {
    instance.delete.mockResolvedValue({ data: { deleted: true } })
    const res = await deleteDocument('abc-123')
    expect(instance.delete).toHaveBeenCalledWith('/documents/abc-123', expect.any(Object))
    expect(res).toEqual({ deleted: true })
  })

  it('sendChat maps params to the backend payload shape', async () => {
    instance.post.mockResolvedValue({ data: { answer: 'ok', sources: [], session_id: 's1' } })
    await sendChat({ question: 'Hi?', sessionId: 's1', topK: 3 })
    const [route, body] = instance.post.mock.calls[0]
    expect(route).toBe('/chat')
    expect(body).toEqual({ question: 'Hi?', session_id: 's1', top_k: 3 })
  })

  it('uploadFiles posts multipart form data and reports progress', async () => {
    instance.post.mockResolvedValue({ data: { files: [] } })
    const onProgress = vi.fn()
    await uploadFiles([new File(['x'], 'a.txt')], onProgress)

    const [route, form, opts] = instance.post.mock.calls[0]
    expect(route).toBe('/upload')
    expect(form).toBeInstanceOf(FormData)
    expect(opts.headers['Content-Type']).toBe('multipart/form-data')

    // Drive the progress callback the way Axios would.
    opts.onUploadProgress({ loaded: 5, total: 10 })
    expect(onProgress).toHaveBeenCalledWith(50)
  })

  it('getMe reads the current user', async () => {
    instance.get.mockResolvedValue({ data: { name: 'Ada', email: 'ada@x.com' } })
    const me = await getMe()
    expect(instance.get).toHaveBeenCalledWith('/auth/me', expect.any(Object))
    expect(me.name).toBe('Ada')
  })

  it('logout clears the token and calls the endpoint best-effort', async () => {
    localStorage.setItem(AUTH_TOKEN_STORAGE, 'tok')
    instance.post.mockResolvedValue({ data: {} })
    await logout()
    expect(localStorage.getItem(AUTH_TOKEN_STORAGE)).toBeNull()
    expect(instance.post).toHaveBeenCalledWith('/auth/logout')
  })
})
