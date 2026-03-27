import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuthStore } from '../store/authStore'
import { approvalsApi } from '../api/approvals'
import StatusBadge from '../components/StatusBadge'
import type { ApprovalRequest } from '../types/approval'

type StatusFilter = 'pending' | 'approved' | 'rejected' | 'all'

const STATUS_TABS: { value: StatusFilter; label: string }[] = [
  { value: 'pending', label: 'Pending' },
  { value: 'approved', label: 'Approved' },
  { value: 'rejected', label: 'Rejected' },
  { value: 'all', label: 'Alle' },
]

interface ExtendedApproval extends ApprovalRequest {
  order_title?: string
  requester_name?: string
  estimated_cost?: number
}

function formatDeadline(isoDate: string): { text: string; colorClass: string } {
  const deadline = new Date(isoDate)
  const now = new Date()
  const diffMs = deadline.getTime() - now.getTime()
  const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24))
  const text = deadline.toLocaleDateString('de-DE')

  if (diffDays < 0) return { text, colorClass: 'text-red-600 font-semibold' }
  if (diffDays <= 2) return { text, colorClass: 'text-orange-500 font-semibold' }
  return { text, colorClass: 'text-gray-700' }
}

export default function Approvals() {
  const token = useAuthStore((s) => s.token)
  const queryClient = useQueryClient()

  const [statusFilter, setStatusFilter] = useState<StatusFilter>('pending')
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const [bulkRejectOpen, setBulkRejectOpen] = useState(false)
  const [bulkRejectReason, setBulkRejectReason] = useState('')

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
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['approvals'] }),
  })

  const allItems: ExtendedApproval[] = data?.items ?? []

  const visibleItems = statusFilter === 'all'
    ? allItems
    : allItems.filter((a) => a.status === statusFilter)

  const pendingItems = visibleItems.filter((a) => a.status === 'pending')

  const isAllSelected =
    pendingItems.length > 0 && pendingItems.every((a) => selected.has(a.id))

  function toggleSelectAll() {
    if (isAllSelected) {
      setSelected(new Set())
    } else {
      setSelected(new Set(pendingItems.map((a) => a.id)))
    }
  }

  function toggleSelect(id: string) {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  function toggleExpand(id: string) {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  async function handleBulkApprove() {
    for (const id of selected) {
      await approveMutation.mutateAsync(id)
    }
    setSelected(new Set())
    queryClient.invalidateQueries({ queryKey: ['approvals'] })
  }

  async function handleBulkReject() {
    if (!bulkRejectReason.trim()) return
    for (const id of selected) {
      await rejectMutation.mutateAsync({ id, reason: bulkRejectReason })
    }
    setSelected(new Set())
    setBulkRejectOpen(false)
    setBulkRejectReason('')
    queryClient.invalidateQueries({ queryKey: ['approvals'] })
  }

  if (isLoading) return <p className="text-sm text-gray-500">Laden...</p>

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Review Requests</h1>

      {/* Status filter tabs */}
      <div className="flex gap-2 mb-4 border-b border-gray-200">
        {STATUS_TABS.map((tab) => (
          <button
            key={tab.value}
            onClick={() => setStatusFilter(tab.value)}
            className={[
              'px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors',
              statusFilter === tab.value
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700',
            ].join(' ')}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Bulk action bar */}
      <div className="flex items-center gap-3 mb-4">
        <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
          <input
            type="checkbox"
            data-testid="select-all"
            checked={isAllSelected}
            onChange={toggleSelectAll}
            className="w-4 h-4 rounded border-gray-300"
          />
          Alle auswählen
        </label>

        <button
          onClick={handleBulkApprove}
          disabled={selected.size === 0 || approveMutation.isPending}
          className="px-4 py-1.5 bg-green-600 text-white text-sm rounded hover:bg-green-700 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Ausgewählte genehmigen
        </button>

        <button
          onClick={() => setBulkRejectOpen(true)}
          disabled={selected.size === 0 || rejectMutation.isPending}
          className="px-4 py-1.5 bg-red-600 text-white text-sm rounded hover:bg-red-700 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Ausgewählte ablehnen
        </button>
      </div>

      {/* Bulk reject dialog */}
      {bulkRejectOpen && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
            <h2 className="text-lg font-semibold mb-3">Ablehnung bestätigen</h2>
            <p className="text-sm text-gray-600 mb-3">
              {selected.size} Anfrage(n) werden abgelehnt. Bitte Grund angeben:
            </p>
            <textarea
              value={bulkRejectReason}
              onChange={(e) => setBulkRejectReason(e.target.value)}
              placeholder="Ablehnungsgrund..."
              className="w-full px-3 py-2 border border-gray-300 rounded text-sm resize-none"
              rows={3}
              data-testid="bulk-reject-reason"
            />
            <div className="flex justify-end gap-2 mt-4">
              <button
                onClick={() => { setBulkRejectOpen(false); setBulkRejectReason('') }}
                className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
              >
                Abbrechen
              </button>
              <button
                onClick={handleBulkReject}
                disabled={!bulkRejectReason.trim() || rejectMutation.isPending}
                className="px-4 py-2 bg-red-600 text-white text-sm rounded hover:bg-red-700 disabled:opacity-40"
              >
                Ablehnen bestätigen
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Approval list */}
      {visibleItems.length === 0 ? (
        <p className="text-sm text-gray-500">Keine Einträge für diesen Filter.</p>
      ) : (
        <div className="space-y-2">
          {visibleItems.map((approval) => {
            const isPending = approval.status === 'pending'
            const isExpanded = expanded.has(approval.id)
            const { text: deadlineText, colorClass: deadlineColor } = formatDeadline(
              approval.deadline_at,
            )

            return (
              <div
                key={approval.id}
                className="border border-gray-200 rounded-lg bg-white overflow-hidden"
              >
                {/* Row summary */}
                <div className="flex items-center gap-3 px-4 py-3">
                  {isPending && (
                    <input
                      type="checkbox"
                      checked={selected.has(approval.id)}
                      onChange={() => toggleSelect(approval.id)}
                      className="w-4 h-4 rounded border-gray-300 shrink-0"
                      aria-label={`Auswählen: ${approval.order_title ?? approval.order_id}`}
                    />
                  )}

                  <button
                    onClick={() => toggleExpand(approval.id)}
                    className="flex-1 text-left"
                    aria-expanded={isExpanded}
                  >
                    <div className="flex items-center justify-between gap-4">
                      <div>
                        <p className="text-sm font-medium text-gray-900">
                          {approval.order_title ?? approval.order_id}
                        </p>
                        <p className="text-xs text-gray-500">
                          {approval.requester_name ?? '—'}
                        </p>
                      </div>
                      <div className="flex items-center gap-4 shrink-0">
                        {approval.estimated_cost !== undefined && (
                          <span className="text-sm text-gray-700">
                            {approval.estimated_cost.toFixed(2)} €/Monat
                          </span>
                        )}
                        <span className={`text-xs ${deadlineColor}`}>{deadlineText}</span>
                        <StatusBadge status={approval.status} />
                        <span className="text-gray-400 text-xs">{isExpanded ? '▲' : '▼'}</span>
                      </div>
                    </div>
                  </button>
                </div>

                {/* Expandable detail section */}
                {isExpanded && (
                  <div className="border-t border-gray-100 px-4 py-3 bg-gray-50 text-sm space-y-4">
                    {/* Bestellinfos */}
                    <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-gray-600">
                      <span className="font-medium">Bestellnummer:</span>
                      <span>{approval.order_number ?? approval.order_id}</span>
                      <span className="font-medium">Bestellt von:</span>
                      <span className="font-semibold">{approval.requester_id ?? '—'}</span>
                      <span className="font-medium">Angefragt am:</span>
                      <span>{new Date(approval.requested_at).toLocaleDateString('de-DE')}</span>
                      <span className="font-medium">Frist:</span>
                      <span className={deadlineColor}>{deadlineText}</span>
                      {approval.business_reason && (
                        <>
                          <span className="font-medium">Geschaeftsgrund:</span>
                          <span>{approval.business_reason}</span>
                        </>
                      )}
                      {approval.decided_by && (
                        <>
                          <span className="font-medium">Entschieden von:</span>
                          <span className="font-semibold">{approval.decided_by}</span>
                        </>
                      )}
                      {approval.decided_at && (
                        <>
                          <span className="font-medium">Entschieden am:</span>
                          <span>{new Date(approval.decided_at).toLocaleDateString('de-DE')}</span>
                        </>
                      )}
                      {approval.decision_reason && (
                        <>
                          <span className="font-medium">Entscheidungsgrund:</span>
                          <span>{approval.decision_reason}</span>
                        </>
                      )}
                    </div>

                    {/* Bestellpositionen */}
                    {approval.order_items && approval.order_items.length > 0 && (
                      <div>
                        <h4 className="font-medium text-gray-700 mb-2">Bestellpositionen</h4>
                        <div className="space-y-2">
                          {approval.order_items.map((oi, idx) => (
                            <div key={idx} className="bg-white border border-gray-200 rounded p-3">
                              <div className="flex items-center justify-between mb-1">
                                <span className="font-medium">{oi.display_name}</span>
                                <div className="flex gap-2 text-xs text-gray-400">
                                  <span>{oi.template_slug} v{oi.template_version}</span>
                                  {oi.quantity > 1 && (
                                    <span className="bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">x{oi.quantity}</span>
                                  )}
                                </div>
                              </div>
                              <div className="grid grid-cols-3 gap-1 text-xs text-gray-500">
                                {Object.entries(oi.parameters).slice(0, 12).map(([k, v]) => (
                                  <span key={k}>{k}: <span className="text-gray-700">{String(v)}</span></span>
                                ))}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {isPending && (
                      <div className="flex gap-2 pt-2">
                        <button
                          onClick={() => approveMutation.mutate(approval.id)}
                          disabled={approveMutation.isPending}
                          className="px-3 py-1 bg-green-600 text-white rounded text-xs hover:bg-green-700 disabled:opacity-50"
                          data-testid={`approve-${approval.id}`}
                        >
                          Genehmigen
                        </button>
                        <button
                          onClick={() => {
                            setSelected(new Set([approval.id]))
                            setBulkRejectOpen(true)
                          }}
                          className="px-3 py-1 bg-red-600 text-white rounded text-xs hover:bg-red-700"
                          data-testid={`reject-${approval.id}`}
                        >
                          Ablehnen
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
