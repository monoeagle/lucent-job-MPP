import { describe, it, expect, vi, beforeEach } from 'vitest'
import { catalogApi } from '../../src/api/catalog'
import { apiClient } from '../../src/api/client'

vi.mock('../../src/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

describe('catalogApi', () => {
  beforeEach(() => vi.clearAllMocks())

  it('listTemplates calls correct URL with filters', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: [], total: 0, limit: 20, offset: 0 })
    await catalogApi.listTemplates('my-token', { type: 'vm', q: 'linux' })
    expect(apiClient.get).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/catalog/templates?'),
      'my-token'
    )
    const url = vi.mocked(apiClient.get).mock.calls[0][0]
    expect(url).toContain('type=vm')
    expect(url).toContain('q=linux')
  })

  it('getTemplate calls correct URL', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ id: '1', slug: 'vm-linux' })
    await catalogApi.getTemplate('my-token', 'vm-linux')
    expect(apiClient.get).toHaveBeenCalledWith('/api/v1/catalog/templates/vm-linux', 'my-token')
  })

  it('getTemplate with version', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ id: '1', slug: 'vm-linux' })
    await catalogApi.getTemplate('my-token', 'vm-linux', '2.0.0')
    expect(apiClient.get).toHaveBeenCalledWith(
      '/api/v1/catalog/templates/vm-linux?version=2.0.0', 'my-token'
    )
  })

  it('getCategories calls correct URL', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ categories: [] })
    await catalogApi.getCategories('my-token')
    expect(apiClient.get).toHaveBeenCalledWith('/api/v1/catalog/categories', 'my-token')
  })
})
