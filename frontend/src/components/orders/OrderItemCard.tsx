import { useState } from 'react'
import type { OrderItem } from '../../types/order'
import StatusBadge from '../StatusBadge'
import ValidationErrors from './ValidationErrors'

interface Props {
  item: OrderItem
  onEdit?: () => void
  onRemove?: () => void
  onCopy?: () => void
  readonly?: boolean
}

export default function OrderItemCard({ item, onEdit, onRemove, onCopy, readonly }: Props) {
  const [expanded, setExpanded] = useState(false)
  const paramEntries = Object.entries(item.parameters)
  const paramSummary = paramEntries
    .slice(0, 4)
    .map(([k, v]) => `${k}: ${String(v)}`)
    .join(', ')

  return (
    <div className="border border-gray-200 rounded-lg bg-white overflow-hidden">
      {/* Header — gesamte Kachel klickbar zum Aufklappen */}
      <div
        className="p-4 cursor-pointer hover:bg-gray-50 transition-colors"
        onClick={() => setExpanded(!expanded)}
        role="button"
        aria-expanded={expanded}
      >
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="text-gray-400 text-xs">{expanded ? '▲' : '▼'}</span>
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
            <div className="flex gap-2" onClick={(e) => e.stopPropagation()}>
              {onCopy && (
                <button onClick={onCopy} className="text-xs text-blue-600 hover:text-blue-800">
                  Ähnlichen hinzufügen
                </button>
              )}
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
        {!expanded && paramSummary && (
          <p className="text-xs text-gray-500 truncate">{paramSummary}</p>
        )}
      </div>

      {/* Detail — aufgeklappt */}
      {expanded && (
        <div className="border-t border-gray-100 bg-gray-50 px-4 py-3">
          <div className="grid grid-cols-2 md:grid-cols-3 gap-x-4 gap-y-1.5 text-sm">
            {paramEntries.map(([key, value]) => (
              <div key={key}>
                <span className="text-gray-500">{key}: </span>
                <span className="text-gray-900 font-medium">{String(value)}</span>
              </div>
            ))}
          </div>
          {item.instance_parameters && item.instance_parameters.length > 0 && (
            <div className="mt-3 pt-3 border-t border-gray-200">
              <p className="text-xs font-medium text-gray-500 mb-2">Instanz-Parameter ({item.instance_parameters.length})</p>
              <div className="space-y-1">
                {item.instance_parameters.map((ip, idx) => (
                  <div key={idx} className="text-xs text-gray-600">
                    #{idx + 1}: {Object.entries(ip).map(([k, v]) => `${k}=${String(v)}`).join(', ')}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {item.validation_state === 'invalid' && (
        <div className="px-4 pb-3">
          <ValidationErrors errors={item.validation_errors} />
        </div>
      )}
    </div>
  )
}
