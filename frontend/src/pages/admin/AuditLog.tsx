import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useAuthStore } from '../../store/authStore'
import { adminApi } from '../../api/admin'

export default function AuditLog() {
  const token = useAuthStore((s) => s.token)
  const [action, setAction] = useState('')
  const [entityType, setEntityType] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  const { data, isLoading } = useQuery({
    queryKey: ['admin-audit-log', action, entityType, dateFrom, dateTo],
    queryFn: () =>
      adminApi.getAuditLog(token!, {
        action: action || undefined,
        entity_type: entityType || undefined,
        from: dateFrom || undefined,
        to: dateTo || undefined,
      }),
    enabled: !!token,
  })

  const handleExport = async () => {
    if (!token) return
    const blob = await adminApi.exportAuditLog(token, {
      from: dateFrom || undefined,
      to: dateTo || undefined,
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'audit-log.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Audit Log</h1>
        <button
          onClick={handleExport}
          className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700"
        >
          Exportieren
        </button>
      </div>

      <div className="flex gap-4 mb-6">
        <input
          type="text"
          placeholder="Aktion filtern..."
          value={action}
          onChange={(e) => setAction(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-md text-sm"
        />
        <input
          type="text"
          placeholder="Entity-Typ filtern..."
          value={entityType}
          onChange={(e) => setEntityType(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-md text-sm"
        />
        <input
          type="date"
          value={dateFrom}
          onChange={(e) => setDateFrom(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-md text-sm"
        />
        <input
          type="date"
          value={dateTo}
          onChange={(e) => setDateTo(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-md text-sm"
        />
      </div>

      {isLoading && <p className="text-sm text-gray-500">Laden...</p>}

      {data && (
        <>
          <p className="text-sm text-gray-500 mb-3">{data.total} Einträge</p>
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Zeitpunkt</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Aktion</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Entity</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Benutzer</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Details</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {data.items.map((entry) => (
                <tr key={entry.id}>
                  <td className="px-4 py-3 text-sm">{new Date(entry.created_at).toLocaleString('de-DE')}</td>
                  <td className="px-4 py-3 text-sm font-medium">{entry.action}</td>
                  <td className="px-4 py-3 text-sm">{entry.entity_type} / {entry.entity_id}</td>
                  <td className="px-4 py-3 text-sm">{entry.user_id}</td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {entry.details ? JSON.stringify(entry.details).slice(0, 80) : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  )
}
