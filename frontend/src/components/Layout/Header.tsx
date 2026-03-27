import { useLocation } from 'react-router-dom'
import GlobalSearch from '../dashboard/GlobalSearch'

const ROUTE_CONFIG: Record<string, { title: string; showSearch?: boolean }> = {
  '/dashboard': { title: 'Dashboard', showSearch: true },
  '/shop': { title: 'Service Catalog' },
  '/workspace': { title: 'Bestellungen' },
  '/notifications': { title: 'Benachrichtigungen' },
  '/reviews': { title: 'Review Requests' },
  '/orders': { title: 'Meine Bestellungen' },
  '/admin': { title: 'Admin Dashboard' },
  '/admin/rules': { title: 'Regelverwaltung' },
  '/admin/audit-log': { title: 'Audit Log' },
}

function getRouteConfig(pathname: string) {
  // Exact match first
  if (ROUTE_CONFIG[pathname]) return ROUTE_CONFIG[pathname]

  // Prefix match for dynamic routes
  if (pathname.startsWith('/shop/') && pathname.includes('/request')) {
    return { title: 'Service bestellen' }
  }
  if (pathname.startsWith('/orders/')) return { title: 'Bestelldetails' }
  if (pathname.startsWith('/subscriptions/')) return { title: 'Subscription Details' }

  return { title: '' }
}

export default function Header() {
  const { pathname } = useLocation()
  const config = getRouteConfig(pathname)

  return (
    <header className="h-14 bg-white border-b border-gray-200 flex items-center justify-between px-6 shrink-0">
      <h1 className="text-lg font-semibold text-gray-800">{config.title}</h1>
      <div className="flex items-center gap-4">
        {config.showSearch && <GlobalSearch />}
      </div>
    </header>
  )
}
