import { NavLink } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'
import { isAdmin, isApprover } from '../../types/common'

const navItems = [
  { to: '/catalog', label: 'Service Catalog', roles: null },
  { to: '/orders', label: 'Meine Bestellungen', roles: null },
  { to: '/resources', label: 'Meine Ressourcen', roles: null },
  { to: '/approvals', label: 'Genehmigungen', roles: ['approver', 'admin'] },
  { to: '/admin/dashboard', label: 'Admin Dashboard', roles: ['admin'] },
  { to: '/admin/rules', label: 'Regelverwaltung', roles: ['admin'] },
  { to: '/admin/audit', label: 'Audit Log', roles: ['admin'] },
]

export default function Sidebar() {
  const user = useAuthStore((s) => s.user)

  const visibleItems = navItems.filter((item) => {
    if (!item.roles) return true
    return item.roles.some((role) => user?.roles.includes(role))
  })

  return (
    <aside className="w-64 bg-gray-900 text-white min-h-screen p-4">
      <div className="text-lg font-bold mb-8 px-2">Marketplace Portal</div>
      <nav className="space-y-1">
        {visibleItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `block px-3 py-2 rounded-md text-sm ${
                isActive ? 'bg-gray-700 text-white' : 'text-gray-300 hover:bg-gray-800 hover:text-white'
              }`
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
