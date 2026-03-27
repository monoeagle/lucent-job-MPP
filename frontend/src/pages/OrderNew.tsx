import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useCreateOrder } from '../hooks/useOrders'

export default function OrderNew() {
  const navigate = useNavigate()
  const createOrder = useCreateOrder()
  const [title, setTitle] = useState('')
  const [businessReason, setBusinessReason] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    createOrder.mutate(
      { title, business_reason: businessReason || undefined },
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
        <button type="submit" disabled={!title || createOrder.isPending}
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
