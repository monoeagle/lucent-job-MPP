import { Navigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'

interface Props {
  children: React.ReactNode
  requiredRoles?: string[]
}

export default function ProtectedRoute({ children, requiredRoles }: Props) {
  const { isAuthenticated, isRestored, user } = useAuthStore()

  if (!isRestored && !isAuthenticated) {
    return null
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  if (requiredRoles && user) {
    const hasRequiredRole = requiredRoles.some((role) => user.roles.includes(role))
    if (!hasRequiredRole) {
      return <Navigate to="/dashboard" replace />
    }
  }

  return <>{children}</>
}
