import { useState } from 'react'
import type { OrderItemGroup } from '../../types/order'
import OrderItemCard from './OrderItemCard'

interface Props {
  group: OrderItemGroup
  isDraft: boolean
  onDeleteGroup?: () => void
  onRemoveItem?: (itemId: string) => void
}

export default function GroupSection({ group, isDraft, onDeleteGroup, onRemoveItem }: Props) {
  const [collapsed, setCollapsed] = useState(false)

  return (
    <div className="border border-gray-300 rounded-lg bg-gray-50">
      <div
        className="flex items-center justify-between p-3 cursor-pointer"
        onClick={() => setCollapsed(!collapsed)}
      >
        <div className="flex items-center gap-2">
          <span className="text-sm">{collapsed ? '▶' : '▼'}</span>
          <span className="font-medium">{group.name}</span>
          <span className="text-xs bg-gray-200 text-gray-600 px-2 py-0.5 rounded-full">
            {group.items.length} {group.items.length === 1 ? 'Item' : 'Items'}
          </span>
        </div>
        {isDraft && onDeleteGroup && group.items.length === 0 && (
          <button
            onClick={(e) => { e.stopPropagation(); onDeleteGroup() }}
            className="text-xs text-red-600 hover:text-red-800"
          >
            Gruppe löschen
          </button>
        )}
      </div>
      {!collapsed && (
        <div className="px-3 pb-3 space-y-2">
          {group.description && (
            <p className="text-xs text-gray-500">{group.description}</p>
          )}
          {group.items.length === 0 ? (
            <p className="text-xs text-gray-400">Keine Items in dieser Gruppe.</p>
          ) : (
            group.items.map((item) => (
              <OrderItemCard
                key={item.id}
                item={item}
                readonly={!isDraft}
                onRemove={isDraft && onRemoveItem ? () => onRemoveItem(item.id) : undefined}
              />
            ))
          )}
        </div>
      )}
    </div>
  )
}
