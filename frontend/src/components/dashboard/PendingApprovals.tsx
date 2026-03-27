import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useAuthStore } from '../../store/authStore'
import { approvalsApi } from '../../api/approvals'

export default function PendingApprovals() {
  const token = useAuthStore((s) => s.token)
  const { data } = useQuery({
    queryKey: ['pending-approvals-dashboard'],
    queryFn: () => approvalsApi.listPendingApprovals(token!),
    enabled: !!token,
  })
  const items = data?.items ?? []

  if (items.length === 0) return null

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">Ausstehende Genehmigungen</h3>
      <div className="space-y-2">
        {items.slice(0, 5).map((a) => (
          <Link
            key={a.id}
            to="/reviews"
            className="flex items-center justify-between text-sm hover:bg-gray-50 rounded px-2 py-1 -mx-2"
          >
            <span>Order {a.order_id.slice(0, 8)}...</span>
            <span className="text-xs text-yellow-600">Ausstehend</span>
          </Link>
        ))}
      </div>
    </div>
  )
}
