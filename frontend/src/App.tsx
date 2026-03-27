import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useEffect } from 'react'
import { useAuthStore } from './store/authStore'
import ProtectedRoute from './components/ProtectedRoute'
import AppLayout from './components/Layout/AppLayout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Catalog from './pages/Catalog'
import Workspace from './pages/Workspace'
import OrderList from './pages/OrderList'
import OrderNew from './pages/OrderNew'
import OrderDetail from './pages/OrderDetail'
import OrderExport from './pages/OrderExport'
import ServiceRequest from './pages/ServiceRequest'
import Notifications from './pages/Notifications'
import Approvals from './pages/Approvals'
import SubscriptionDetail from './pages/SubscriptionDetail'
import AdminDashboard from './pages/admin/Dashboard'
import Rules from './pages/admin/Rules'
import AuditLog from './pages/admin/AuditLog'
import AdminConfig from './pages/admin/Config'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 30_000 },
  },
})

function AppRoutes() {
  const restoreSession = useAuthStore((s) => s.restoreSession)

  useEffect(() => {
    restoreSession()
  }, [restoreSession])

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/shop" element={<Catalog />} />
        <Route path="/shop/:slug/request" element={<ServiceRequest />} />
        <Route path="/workspace" element={<Workspace />} />
        <Route path="/orders" element={<OrderList />} />
        <Route path="/orders/new" element={<OrderNew />} />
        <Route path="/orders/:orderId" element={<OrderDetail />} />
        <Route path="/orders/:orderId/export" element={<OrderExport />} />
        <Route path="/notifications" element={<Notifications />} />
        <Route
          path="/reviews"
          element={
            <ProtectedRoute requiredRoles={['approver', 'admin']}>
              <Approvals />
            </ProtectedRoute>
          }
        />
        <Route path="/subscriptions/:id" element={<SubscriptionDetail />} />
        <Route
          path="/admin"
          element={
            <ProtectedRoute requiredRoles={['admin', 'superadmin']}>
              <AdminDashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/rules"
          element={
            <ProtectedRoute requiredRoles={['superadmin']}>
              <Rules />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/audit-log"
          element={
            <ProtectedRoute requiredRoles={['superadmin']}>
              <AuditLog />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/config"
          element={
            <ProtectedRoute requiredRoles={['admin', 'superadmin']}>
              <AdminConfig />
            </ProtectedRoute>
          }
        />
        {/* Redirects from old paths */}
        <Route path="/catalog" element={<Navigate to="/shop" replace />} />
        <Route path="/my-services" element={<Navigate to="/workspace" replace />} />
        <Route path="/my-requests" element={<Navigate to="/workspace" replace />} />
        <Route path="/approvals" element={<Navigate to="/reviews" replace />} />
        <Route path="/resources" element={<Navigate to="/workspace" replace />} />
        <Route path="/subscriptions" element={<Navigate to="/workspace" replace />} />
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </QueryClientProvider>
  )
}
