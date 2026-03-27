import type { OrderItem } from '../../types/order'
import StatusBadge from '../StatusBadge'
import ValidationErrors from './ValidationErrors'

interface Props {
  item: OrderItem
  onEdit?: () => void
  onRemove?: () => void
  readonly?: boolean
}

export default function OrderItemCard({ item, onEdit, onRemove, readonly }: Props) {
  const paramSummary = Object.entries(item.parameters)
    .slice(0, 4)
    .map(([k, v]) => `${k}: ${String(v)}`)
    .join(', ')

  return (
    <div className="border border-gray-200 rounded-lg p-4 bg-white">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">{item.display_name}</span>
          <span className="text-xs text-gray-400">v{item.template_version}</span>
          <StatusBadge status={item.validation_state} />
          {item.quantity > 1 && (
            <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">
              ×{item.quantity}
            </span>
          )}
        </div>
        {!readonly && (
          <div className="flex gap-2">
            {onEdit && (
              <button onClick={onEdit} className="text-xs text-blue-600 hover:text-blue-800">
                Bearbeiten
              </button>
            )}
            {onRemove && (
              <button onClick={onRemove} className="text-xs text-red-600 hover:text-red-800">
                Entfernen
              </button>
            )}
          </div>
        )}
      </div>
      {paramSummary && (
        <p className="text-xs text-gray-500 truncate">{paramSummary}</p>
      )}
      {item.validation_state === 'invalid' && (
        <ValidationErrors errors={item.validation_errors} />
      )}
    </div>
  )
}
