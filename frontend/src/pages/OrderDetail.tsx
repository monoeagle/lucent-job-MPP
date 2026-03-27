import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useOrder, useAddItem, useRemoveItem, useValidateOrder, useSubmitOrder, useDeleteOrder } from '../hooks/useOrders'
import { useOrderStatus } from '../hooks/useOrderStatus'
import { useTemplates, useTemplate } from '../hooks/useCatalog'
import StatusBadge from '../components/StatusBadge'
import Drawer from '../components/Drawer'
import OrderItemCard from '../components/orders/OrderItemCard'
import OrderActions from '../components/orders/OrderActions'
import ParameterForm from '../components/ParameterForm/ParameterForm'

export default function OrderDetail() {
  const { orderId } = useParams<{ orderId: string }>()
  const navigate = useNavigate()
  const { data: order, isLoading, error } = useOrder(orderId ?? null)
  useOrderStatus(orderId ?? null, order?.status ?? null)

  const addItem = useAddItem(orderId ?? '')
  const removeItem = useRemoveItem(orderId ?? '')
  const validateOrder = useValidateOrder(orderId ?? '')
  const submitOrder = useSubmitOrder(orderId ?? '')
  const deleteOrder = useDeleteOrder()

  const [drawerOpen, setDrawerOpen] = useState(false)
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null)
  const [itemParams, setItemParams] = useState<Record<string, unknown>>({})

  const { data: templatesData } = useTemplates()
  const { data: templateDetail } = useTemplate(selectedSlug)

  const templates = templatesData?.data ?? []
  const isDraft = order?.status === 'draft'

  const handleAddItem = () => {
    if (!selectedSlug || !templateDetail) return
    addItem.mutate(
      { template_slug: selectedSlug, template_version: templateDetail.version, parameters: itemParams },
      {
        onSuccess: () => {
          setDrawerOpen(false)
          setSelectedSlug(null)
          setItemParams({})
        },
      },
    )
  }

  const handleDelete = () => {
    if (!orderId) return
    deleteOrder.mutate(orderId, { onSuccess: () => navigate('/orders') })
  }

  if (isLoading) return <p className="text-gray-500">Lade Bestellung...</p>
  if (error || !order) return <p className="text-red-500">Fehler beim Laden der Bestellung.</p>

  return (
    <div>
      <div className="flex items-center gap-4 mb-6">
        <div>
          <p className="text-sm text-gray-400">{order.order_number}</p>
          <h1 className="text-2xl font-bold">{order.title}</h1>
        </div>
        <StatusBadge status={order.status} />
      </div>

      {order.business_reason && (
        <p className="text-sm text-gray-600 mb-4">{order.business_reason}</p>
      )}

      <OrderActions
        orderId={order.id}
        status={order.status}
        onValidate={() => validateOrder.mutate()}
        onSubmit={() => submitOrder.mutate()}
        onDelete={handleDelete}
        isValidating={validateOrder.isPending}
        isSubmitting={submitOrder.isPending}
      />

      <div className="mt-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Positionen ({order.items.length})</h2>
          {isDraft && (
            <button onClick={() => setDrawerOpen(true)}
              className="px-3 py-1.5 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700">
              Service hinzufügen
            </button>
          )}
        </div>

        {order.items.length === 0 ? (
          <p className="text-gray-400 text-sm">Noch keine Positionen vorhanden.</p>
        ) : (
          <div className="space-y-3">
            {order.items
              .sort((a, b) => a.position - b.position)
              .map((item) => (
                <OrderItemCard
                  key={item.id}
                  item={item}
                  readonly={!isDraft}
                  onRemove={isDraft ? () => removeItem.mutate(item.id) : undefined}
                />
              ))}
          </div>
        )}
      </div>

      <Drawer open={drawerOpen} onClose={() => setDrawerOpen(false)} title="Service hinzufügen">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Service-Template</label>
            <select value={selectedSlug ?? ''} onChange={(e) => { setSelectedSlug(e.target.value || null); setItemParams({}) }}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm">
              <option value="">Bitte wählen...</option>
              {templates.map((t) => (
                <option key={t.slug} value={t.slug}>{t.display_name}</option>
              ))}
            </select>
          </div>

          {templateDetail && templateDetail.parameters.length > 0 && (
            <ParameterForm
              parameters={templateDetail.parameters}
              values={itemParams}
              onChange={(key, val) => setItemParams((prev) => ({ ...prev, [key]: val }))}
            />
          )}

          <button onClick={handleAddItem} disabled={!selectedSlug || addItem.isPending}
            className="w-full px-4 py-2 bg-green-600 text-white rounded-md text-sm hover:bg-green-700 disabled:opacity-50">
            {addItem.isPending ? 'Wird hinzugefügt...' : 'Hinzufügen'}
          </button>
        </div>
      </Drawer>
    </div>
  )
}
