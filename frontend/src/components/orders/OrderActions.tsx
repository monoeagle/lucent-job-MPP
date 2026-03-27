import { useNavigate } from 'react-router-dom'

interface Props {
  orderId: string
  status: string
  onValidate: () => void
  onSubmit: () => void
  onDelete: () => void
  isValidating?: boolean
  isSubmitting?: boolean
}

export default function OrderActions({ orderId, status, onValidate, onSubmit, onDelete, isValidating, isSubmitting }: Props) {
  const navigate = useNavigate()
  const isDraft = status === 'draft'
  const isValidated = status === 'validated'
  const canExport = ['submitted', 'approved', 'provisioning', 'done'].includes(status)

  return (
    <div className="flex gap-2 flex-wrap">
      {isDraft && (
        <button onClick={onValidate} disabled={isValidating}
          className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700 disabled:opacity-50">
          {isValidating ? 'Validiere...' : 'Validieren'}
        </button>
      )}
      {(isDraft || isValidated) && (
        <button onClick={onSubmit} disabled={isSubmitting || isDraft}
          className="px-4 py-2 bg-green-600 text-white rounded-md text-sm hover:bg-green-700 disabled:opacity-50">
          {isSubmitting ? 'Wird eingereicht...' : 'Einreichen'}
        </button>
      )}
      {canExport && (
        <button onClick={() => navigate(`/orders/${orderId}/export`)}
          className="px-4 py-2 bg-gray-600 text-white rounded-md text-sm hover:bg-gray-700">
          Export
        </button>
      )}
      {isDraft && (
        <button onClick={onDelete}
          className="px-4 py-2 bg-red-600 text-white rounded-md text-sm hover:bg-red-700">
          Löschen
        </button>
      )}
    </div>
  )
}
