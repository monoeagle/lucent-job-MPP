import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ordersApi } from '../../src/api/orders'
import { apiClient } from '../../src/api/client'

vi.mock('../../src/api/client', () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), put: vi.fn(), del: vi.fn() },
}))

describe('ordersApi', () => {
  beforeEach(() => vi.clearAllMocks())

  it('createOrder posts correct body', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ id: '1', status: 'draft' })
    await ordersApi.createOrder('tok', { title: 'Test', business_reason: 'reason' })
    expect(apiClient.post).toHaveBeenCalledWith('/api/v1/orders',
      { title: 'Test', business_reason: 'reason' }, 'tok')
  })

  it('getOrder calls correct URL', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ id: '1' })
    await ordersApi.getOrder('tok', 'order-1')
    expect(apiClient.get).toHaveBeenCalledWith('/api/v1/orders/order-1', 'tok')
  })

  it('addItem posts to correct URL', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ item: { id: 'i1' } })
    await ordersApi.addItem('tok', 'o1', { template_slug: 'vm', template_version: '1.0.0', parameters: {} })
    expect(apiClient.post).toHaveBeenCalledWith('/api/v1/orders/o1/items',
      { template_slug: 'vm', template_version: '1.0.0', parameters: {} }, 'tok')
  })

  it('validateOrder posts to validate URL', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ all_valid: true })
    await ordersApi.validateOrder('tok', 'o1')
    expect(apiClient.post).toHaveBeenCalledWith('/api/v1/orders/o1/validate', undefined, 'tok')
  })

  it('submitOrder posts to submit URL', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ status: 'submitted' })
    await ordersApi.submitOrder('tok', 'o1')
    expect(apiClient.post).toHaveBeenCalledWith('/api/v1/orders/o1/submit', undefined, 'tok')
  })

  it('getExport calls export URL', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ items: [] })
    await ordersApi.getExport('tok', 'o1')
    expect(apiClient.get).toHaveBeenCalledWith('/api/v1/orders/o1/export/tofu', 'tok')
  })

  it('deleteOrder calls del', async () => {
    vi.mocked(apiClient.del).mockResolvedValue(undefined)
    await ordersApi.deleteOrder('tok', 'o1')
    expect(apiClient.del).toHaveBeenCalledWith('/api/v1/orders/o1', 'tok')
  })
})
