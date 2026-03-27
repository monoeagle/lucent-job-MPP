import { Link } from 'react-router-dom'
import type { DashboardStats } from '../../api/dashboard'

interface Props {
  templates: DashboardStats['popular_templates']
}

export default function PopularServices({ templates }: Props) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">Beliebte Services</h3>
      {templates.length === 0 ? (
        <p className="text-sm text-gray-400">Keine Services bestellt</p>
      ) : (
        <div className="space-y-2">
          {templates.map((t) => (
            <div key={t.slug} className="flex items-center justify-between text-sm">
              <div>
                <span className="font-medium">{t.display_name}</span>
                <span className="text-xs text-gray-400 ml-2">{t.category}</span>
              </div>
              <Link to={`/shop/${t.slug}/request`} className="text-xs text-blue-600 hover:text-blue-800">
                Bestellen
              </Link>
            </div>
          ))}
          <Link to="/shop" className="text-xs text-blue-600 hover:text-blue-800">
            Zum Shop →
          </Link>
        </div>
      )}
    </div>
  )
}
