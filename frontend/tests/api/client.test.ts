import { describe, it, expect, vi, beforeEach } from 'vitest'
import { apiClient } from '../../src/api/client'

describe('apiClient', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('adds auth header when token is provided', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ status: 'ok' }),
      headers: new Headers({ 'content-type': 'application/json' }),
    })
    vi.stubGlobal('fetch', mockFetch)

    await apiClient.get('/api/v1/health', 'test-token')

    expect(mockFetch).toHaveBeenCalledWith('/api/v1/health', expect.objectContaining({
      headers: expect.objectContaining({
        Authorization: 'Bearer test-token',
      }),
    }))
  })

  it('does not add auth header when no token', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ status: 'ok' }),
      headers: new Headers({ 'content-type': 'application/json' }),
    })
    vi.stubGlobal('fetch', mockFetch)

    await apiClient.get('/api/v1/health')

    const calledHeaders = mockFetch.mock.calls[0][1].headers
    expect(calledHeaders.Authorization).toBeUndefined()
  })

  it('throws ApiError on 4xx response', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      json: () => Promise.resolve({
        error_code: 'NOT_FOUND',
        message: 'Not found',
        details: null,
        request_id: 'req-1',
      }),
      headers: new Headers({ 'content-type': 'application/json' }),
    })
    vi.stubGlobal('fetch', mockFetch)

    const { ApiError } = await import('../../src/types/common')
    await expect(apiClient.get('/api/v1/missing')).rejects.toThrow(ApiError)
  })

  it('posts JSON body', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ success: true }),
      headers: new Headers({ 'content-type': 'application/json' }),
    })
    vi.stubGlobal('fetch', mockFetch)

    await apiClient.post('/api/v1/test', { key: 'value' }, 'token')

    expect(mockFetch).toHaveBeenCalledWith('/api/v1/test', expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({ key: 'value' }),
    }))
  })
})
