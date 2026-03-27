import { useQuery } from '@tanstack/react-query'
import { useAuthStore } from '../store/authStore'
import { resourcesApi } from '../api/resources'
import { Link } from 'react-router-dom'
import StatusBadge from '../components/StatusBadge'

export default function Resources() {
  const token = useAuthStore((s) => s.token)

  const { data, isLoading } = useQuery({
    queryKey: ['resources'],
    queryFn: () => resourcesApi.listResources(token!),
    enabled: !!token,
  })

  if (isLoading) return <p className="text-sm text-gray-500">Laden...</p>

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Ressourcen</h1>

      {!data?.items.length ? (
        <p className="text-sm text-gray-500">Keine Ressourcen vorhanden.</p>
      ) : (
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Template</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Parameter</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Bestellung</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {data.items.map((resource) => (
              <tr key={resource.id}>
                <td className="px-4 py-3 text-sm font-medium">{resource.display_name}</td>
                <td className="px-4 py-3 text-sm">{resource.template_slug}</td>
                <td className="px-4 py-3 text-sm text-gray-500">
                  {Object.entries(resource.parameters).slice(0, 3).map(([k, v]) => (
                    <span key={k} className="mr-2">{k}: {String(v)}</span>
                  ))}
                  {Object.keys(resource.parameters).length > 3 && <span>...</span>}
                </td>
                <td className="px-4 py-3"><StatusBadge status={resource.status} /></td>
                <td className="px-4 py-3 text-sm">
                  <Link to={`/orders/${resource.order_id}`} className="text-blue-600 hover:underline">
                    {resource.order_number}
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
