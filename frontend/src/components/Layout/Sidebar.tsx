import { useState, useEffect } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'
import { useUnreadCount } from '../../hooks/useNotifications'

const STORAGE_KEY = 'mpp-sidebar-collapsed'

interface NavItem {
  to: string
  label: string
  icon: string
  roles: string[] | null
  disabled?: boolean
}

const mainItems: NavItem[] = [
  { to: '/dashboard', label: 'Dashboard', icon: '📊', roles: null },
  { to: '/shop', label: 'Shop', icon: '🛒', roles: null },
  { to: '/my-services', label: 'My Services', icon: '📋', roles: null },
  { to: '/my-requests', label: 'My Requests', icon: '📝', roles: null },
  { to: '/notifications', label: 'Notifications', icon: '🔔', roles: null },
  { to: '/reviews', label: 'Review Requests', icon: '✅', roles: ['approver', 'admin'] },
]

const adminItems: NavItem[] = [
  { to: '/admin', label: 'Admin Dashboard', icon: '⚙', roles: ['admin'] },
  { to: '/admin/rules', label: 'Rules', icon: '📏', roles: ['admin'] },
  { to: '/admin/audit-log', label: 'Audit Log', icon: '📜', roles: ['admin'] },
]

function NavItemLink({ item, collapsed, badge }: { item: NavItem; collapsed: boolean; badge?: number }) {
  if (item.disabled) {
    return (
      <div
        className="flex items-center gap-3 px-3 py-2 rounded-md text-sm text-gray-500 opacity-50 cursor-not-allowed"
        title="Kommt bald"
      >
        <span className="text-base w-5 text-center">{item.icon}</span>
        {!collapsed && <span>{item.label}</span>}
      </div>
    )
  }

  return (
    <NavLink
      to={item.to}
      title={collapsed ? item.label : undefined}
      className={({ isActive }) =>
        `relative flex items-center gap-3 px-3 py-2 rounded-md text-sm ${
          isActive
            ? 'bg-gray-700 text-white'
            : 'text-gray-300 hover:bg-gray-800 hover:text-white'
        }`
      }
    >
      <span className="relative text-base w-5 text-center">
        {item.icon}
        {badge !== undefined && badge > 0 && collapsed && (
          <span className="absolute -top-1 -right-1 bg-red-500 rounded-full w-2 h-2" />
        )}
      </span>
      {!collapsed && <span>{item.label}</span>}
      {badge !== undefined && badge > 0 && !collapsed && (
        <span className="ml-auto bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
          {badge > 99 ? '99+' : badge}
        </span>
      )}
    </NavLink>
  )
}

export default function Sidebar() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()
  const { data: unreadData } = useUnreadCount()
  const unreadCount = unreadData?.count ?? 0
  const [collapsed, setCollapsed] = useState(() => {
    return localStorage.getItem(STORAGE_KEY) === 'true'
  })

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, String(collapsed))
  }, [collapsed])

  const isVisible = (item: NavItem) => {
    if (!item.roles) return true
    return item.roles.some((role) => user?.roles.includes(role))
  }

  const visibleMain = mainItems.filter(isVisible)
  const visibleAdmin = adminItems.filter(isVisible)

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <aside
      data-testid="sidebar"
      className={`${collapsed ? 'w-16' : 'w-60'} bg-gray-900 text-white h-screen flex flex-col transition-all duration-200 shrink-0 overflow-y-auto`}
    >
      <div className="flex items-center justify-between p-4">
        {!collapsed && <span className="text-lg font-bold">MPP</span>}
        <button
          data-testid="sidebar-toggle"
          onClick={() => setCollapsed(!collapsed)}
          className="text-gray-400 hover:text-white p-1"
        >
          {collapsed ? '»' : '«'}
        </button>
      </div>

      <nav className="flex-1 px-2 space-y-1">
        {visibleMain.map((item) => (
          <NavItemLink
            key={item.label}
            item={item}
            collapsed={collapsed}
            badge={item.to === '/notifications' ? unreadCount : undefined}
          />
        ))}

        {visibleAdmin.length > 0 && (
          <>
            <div className="border-t border-gray-700 my-3" />
            {visibleAdmin.map((item) => (
              <NavItemLink key={item.label} item={item} collapsed={collapsed} />
            ))}
          </>
        )}
      </nav>

      <div className="border-t border-gray-700 p-3">
        <div className="flex items-center gap-3 px-1">
          <span className="text-base">👤</span>
          {!collapsed && (
            <div className="flex-1 min-w-0">
              <div className="text-sm text-gray-300 truncate">{user?.display_name}</div>
              <button
                onClick={handleLogout}
                className="text-xs text-gray-500 hover:text-gray-300"
              >
                Abmelden
              </button>
            </div>
          )}
        </div>
      </div>
    </aside>
  )
}
