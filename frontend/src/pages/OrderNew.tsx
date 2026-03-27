import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useCreateOrder } from '../hooks/useOrders'
import ContextSelector from '../components/orders/ContextSelector'
import type { OrderContext } from '../types/context'

export default function OrderNew() {
  const navigate = useNavigate()
  const createOrder = useCreateOrder()
  const [title, setTitle] = useState('')
  const [businessReason, setBusinessReason] = useState('')
  const [context, setContext] = useState<OrderContext | null>(null)

  const handleContextChange = useCallback((ctx: OrderContext) => {
    setContext(ctx)
  }, [])

  const isContextComplete = context?.location_id && context?.tenant_id && context?.security_zone_id

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!isContextComplete) return

    createOrder.mutate(
      {
        title,
        business_reason: businessReason || undefined,
        context: {
          location_id: context.location_id,
          tenant_id: context.tenant_id,
          security_zone_id: context.security_zone_id,
          ...(context.network_id ? { network_id: context.network_id } : {}),
        },
      },
      { onSuccess: (order) => navigate(`/orders/${order.id}`) },
    )
  }

  return (
    <div className="max-w-lg">
      <h1 className="text-2xl font-bold mb-6">Neue Bestellung</h1>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Titel *</label>
          <input type="text" value={title} onChange={(e) => setTitle(e.target.value)}
            required className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Geschäftsgrund</label>
          <textarea value={businessReason} onChange={(e) => setBusinessReason(e.target.value)}
            rows={3} className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm" />
        </div>

        <div className="border-t pt-4">
          <h2 className="text-lg font-semibold mb-3">Kontext</h2>
          <ContextSelector value={context} onChange={handleContextChange} />
        </div>

        <button type="submit" disabled={!title || !isContextComplete || createOrder.isPending}
          className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700 disabled:opacity-50">
          {createOrder.isPending ? 'Erstelle...' : 'Bestellung erstellen'}
        </button>
        {createOrder.isError && (
          <p className="text-sm text-red-500">Fehler beim Erstellen der Bestellung.</p>
        )}
      </form>
    </div>
  )
}
