import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import type { OrderItem } from '../types/order'
import { useOrder, useAddItem, useRemoveItem, useValidateOrder, useSubmitOrder, useDeleteOrder, useCreateGroup, useDeleteGroup } from '../hooks/useOrders'
import { useOrderStatus } from '../hooks/useOrderStatus'
import { useTemplates, useTemplate } from '../hooks/useCatalog'
import StatusBadge from '../components/StatusBadge'
import Drawer from '../components/Drawer'
import OrderItemCard from '../components/orders/OrderItemCard'
import OrderActions from '../components/orders/OrderActions'
import GroupSection from '../components/orders/GroupSection'
import QuantitySelector from '../components/orders/QuantitySelector'
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
  const createGroup = useCreateGroup(orderId ?? '')
  const deleteGroup = useDeleteGroup(orderId ?? '')

  const [drawerOpen, setDrawerOpen] = useState(false)
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null)
  const [itemParams, setItemParams] = useState<Record<string, unknown>>({})
  const [quantity, setQuantity] = useState(1)
  const [groupDialogOpen, setGroupDialogOpen] = useState(false)
  const [newGroupName, setNewGroupName] = useState('')

  const { data: templatesData } = useTemplates()
  const { data: templateDetail } = useTemplate(selectedSlug)

  const user = useAuthStore((s) => s.user)
  const templates = templatesData?.data ?? []
  const isDraft = order?.status === 'draft'
  const isAdmin = user?.roles.includes('admin') ?? false
  const isEditable = isDraft || isAdmin

  const handleAddItem = () => {
    if (!selectedSlug || !templateDetail) return
    addItem.mutate(
      {
        template_slug: selectedSlug,
        template_version: templateDetail.version,
        parameters: itemParams,
        quantity: quantity > 1 ? quantity : undefined,
      },
      {
        onSuccess: () => {
          setDrawerOpen(false)
          setSelectedSlug(null)
          setItemParams({})
          setQuantity(1)
        },
      },
    )
  }

  const handleCreateGroup = () => {
    if (!newGroupName.trim()) return
    createGroup.mutate(
      { name: newGroupName.trim() },
      {
        onSuccess: () => {
          setGroupDialogOpen(false)
          setNewGroupName('')
        },
      },
    )
  }

  const handleCopyItem = (item: OrderItem) => {
    navigate(`/shop/${item.template_slug}/request?orderId=${orderId}`)
  }

  const handleDelete = () => {
    if (!orderId) return
    deleteOrder.mutate(orderId, { onSuccess: () => navigate('/orders') })
  }

  if (isLoading) return <p className="text-gray-500">Lade Bestellung...</p>
  if (error || !order) return <p className="text-red-500">Fehler beim Laden der Bestellung.</p>

  const groups = order.groups ?? []
  const ungroupedItems = order.ungrouped_items ?? order.items

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
          {isEditable && (
            <div className="flex gap-2">
              <button onClick={() => setGroupDialogOpen(true)}
                className="px-3 py-1.5 border border-gray-300 text-gray-700 rounded-md text-sm hover:bg-gray-50">
                Neue Gruppe
              </button>
              <button onClick={() => setDrawerOpen(true)}
                className="px-3 py-1.5 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700">
                Service hinzufügen
              </button>
            </div>
          )}
        </div>

        {/* Groups */}
        {groups.length > 0 && (
          <div className="space-y-3 mb-4">
            {groups
              .sort((a, b) => a.position - b.position)
              .map((group) => (
                <GroupSection
                  key={group.id}
                  group={group}
                  isDraft={isEditable}
                  onDeleteGroup={() => deleteGroup.mutate(group.id)}
                  onRemoveItem={(itemId) => removeItem.mutate(itemId)}
                  onCopyItem={(item) => handleCopyItem(item)}
                />
              ))}
          </div>
        )}

        {/* Ungrouped items */}
        {ungroupedItems.length === 0 && groups.length === 0 ? (
          <p className="text-gray-400 text-sm">Noch keine Positionen vorhanden.</p>
        ) : ungroupedItems.length > 0 ? (
          <div className="space-y-3">
            {groups.length > 0 && (
              <h3 className="text-sm font-medium text-gray-500">Ohne Gruppe</h3>
            )}
            {ungroupedItems
              .sort((a, b) => a.position - b.position)
              .map((item) => (
                <OrderItemCard
                  key={item.id}
                  item={item}
                  readonly={!isEditable}
                  onRemove={isEditable ? () => removeItem.mutate(item.id) : undefined}
                  onCopy={isEditable ? () => handleCopyItem(item) : undefined}
                />
              ))}
          </div>
        ) : null}
      </div>

      {/* Add item drawer */}
      <Drawer open={drawerOpen} onClose={() => setDrawerOpen(false)} title="Service hinzufügen">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Service-Template</label>
            <select value={selectedSlug ?? ''} onChange={(e) => { setSelectedSlug(e.target.value || null); setItemParams({}); setQuantity(1) }}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm">
              <option value="">Bitte wählen...</option>
              {templates.map((t) => (
                <option key={t.slug} value={t.slug}>{t.display_name}</option>
              ))}
            </select>
          </div>

          {selectedSlug && <QuantitySelector value={quantity} onChange={setQuantity} />}

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

      {/* Create group dialog */}
      {groupDialogOpen && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-96 shadow-xl">
            <h3 className="text-lg font-semibold mb-4">Neue Gruppe erstellen</h3>
            <input
              type="text"
              value={newGroupName}
              onChange={(e) => setNewGroupName(e.target.value)}
              placeholder="Gruppenname"
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm mb-4"
              autoFocus
            />
            <div className="flex gap-2 justify-end">
              <button onClick={() => { setGroupDialogOpen(false); setNewGroupName('') }}
                className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">
                Abbrechen
              </button>
              <button onClick={handleCreateGroup}
                disabled={!newGroupName.trim() || createGroup.isPending}
                className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700 disabled:opacity-50">
                Erstellen
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
