import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuthStore } from '../store/authStore'
import { approvalsApi } from '../api/approvals'
import StatusBadge from '../components/StatusBadge'

export default function Approvals() {
  const token = useAuthStore((s) => s.token)
  const queryClient = useQueryClient()
  const [rejectId, setRejectId] = useState<string | null>(null)
  const [rejectReason, setRejectReason] = useState('')

  const { data, isLoading } = useQuery({
    queryKey: ['approvals'],
    queryFn: () => approvalsApi.listPendingApprovals(token!),
    enabled: !!token,
  })

  const approveMutation = useMutation({
    mutationFn: (id: string) => approvalsApi.approve(token!, id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['approvals'] }),
  })

  const rejectMutation = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      approvalsApi.reject(token!, id, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['approvals'] })
      setRejectId(null)
      setRejectReason('')
    },
  })

  const handleReject = (id: string) => {
    if (!rejectReason.trim()) return
    rejectMutation.mutate({ id, reason: rejectReason })
  }

  if (isLoading) return <p className="text-sm text-gray-500">Laden...</p>

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Genehmigungen</h1>

      {!data?.items.length ? (
        <p className="text-sm text-gray-500">Keine ausstehenden Genehmigungen.</p>
      ) : (
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Bestell-ID</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Angefragt</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Frist</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Aktionen</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {data.items.map((approval) => (
              <tr key={approval.id}>
                <td className="px-4 py-3 text-sm">{approval.order_id}</td>
                <td className="px-4 py-3"><StatusBadge status={approval.status} /></td>
                <td className="px-4 py-3 text-sm">{new Date(approval.requested_at).toLocaleDateString('de-DE')}</td>
                <td className="px-4 py-3 text-sm">{new Date(approval.deadline_at).toLocaleDateString('de-DE')}</td>
                <td className="px-4 py-3 text-sm space-x-2">
                  <button
                    onClick={() => approveMutation.mutate(approval.id)}
                    disabled={approveMutation.isPending}
                    className="px-3 py-1 bg-green-600 text-white rounded text-xs hover:bg-green-700 disabled:opacity-50"
                    data-testid={`approve-${approval.id}`}
                  >
                    Genehmigen
                  </button>
                  {rejectId === approval.id ? (
                    <span className="inline-flex items-center gap-2">
                      <textarea
                        value={rejectReason}
                        onChange={(e) => setRejectReason(e.target.value)}
                        placeholder="Ablehnungsgrund..."
                        className="px-2 py-1 border border-gray-300 rounded text-xs"
                        rows={1}
                        data-testid="reject-reason"
                      />
                      <button
                        onClick={() => handleReject(approval.id)}
                        disabled={!rejectReason.trim() || rejectMutation.isPending}
                        className="px-3 py-1 bg-red-600 text-white rounded text-xs hover:bg-red-700 disabled:opacity-50"
                      >
                        Bestätigen
                      </button>
                      <button onClick={() => { setRejectId(null); setRejectReason('') }}
                        className="px-2 py-1 text-gray-500 text-xs">
                        Abbrechen
                      </button>
                    </span>
                  ) : (
                    <button
                      onClick={() => setRejectId(approval.id)}
                      className="px-3 py-1 bg-red-600 text-white rounded text-xs hover:bg-red-700"
                      data-testid={`reject-${approval.id}`}
                    >
                      Ablehnen
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
