import { useLocation } from 'react-router-dom'
import { useState, useEffect } from 'react'
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
  if (ROUTE_CONFIG[pathname]) return ROUTE_CONFIG[pathname]

  if (pathname.startsWith('/shop/') && pathname.includes('/request')) {
    return { title: 'Service bestellen', isRequest: true }
  }
  if (pathname.startsWith('/orders/')) return { title: 'Bestelldetails' }
  if (pathname.startsWith('/subscriptions/')) return { title: 'Subscription Details' }

  return { title: '' }
}

function ViewToggle() {
  const { pathname } = useLocation()
  const slug = pathname.split('/')[2] ?? ''

  const [view, setView] = useState<'wizard' | 'form'>(() => {
    const stored = localStorage.getItem(`mpp-view-${slug}`)
    return stored === 'form' ? 'form' : 'wizard'
  })

  useEffect(() => {
    const stored = localStorage.getItem(`mpp-view-${slug}`)
    setView(stored === 'form' ? 'form' : 'wizard')
  }, [slug])

  const toggle = () => {
    const next = view === 'wizard' ? 'form' : 'wizard'
    setView(next)
    localStorage.setItem(`mpp-view-${slug}`, next)
    // Dispatch custom event so ServiceRequest picks up the change
    window.dispatchEvent(new CustomEvent('mpp-view-toggle', { detail: next }))
  }

  return (
    <button
      data-testid="view-toggle"
      onClick={toggle}
      className="px-3 py-1.5 border border-gray-300 rounded-md text-sm text-gray-600 hover:bg-gray-50"
    >
      {view === 'wizard' ? '≡ Formular-Ansicht' : '☰ Wizard-Ansicht'}
    </button>
  )
}

export default function Header() {
  const { pathname } = useLocation()
  const config = getRouteConfig(pathname) as { title: string; showSearch?: boolean; isRequest?: boolean }

  return (
    <header className="h-14 bg-white border-b border-gray-200 flex items-center justify-between px-6 shrink-0">
      <h1 className="text-lg font-semibold text-gray-800">{config.title}</h1>
      <div className="flex items-center gap-4">
        {config.showSearch && <GlobalSearch />}
        {config.isRequest && <ViewToggle />}
      </div>
    </header>
  )
}
