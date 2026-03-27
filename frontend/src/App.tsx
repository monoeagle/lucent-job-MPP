import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useEffect } from 'react'
import { useAuthStore } from './store/authStore'
import ProtectedRoute from './components/ProtectedRoute'
import AppLayout from './components/Layout/AppLayout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Catalog from './pages/Catalog'
import OrderList from './pages/OrderList'
import OrderNew from './pages/OrderNew'
import OrderDetail from './pages/OrderDetail'
import OrderExport from './pages/OrderExport'
import ServiceRequest from './pages/ServiceRequest'
import Approvals from './pages/Approvals'
import Resources from './pages/Resources'
import Notifications from './pages/Notifications'
import Subscriptions from './pages/Subscriptions'
import SubscriptionDetail from './pages/SubscriptionDetail'
import AdminDashboard from './pages/admin/Dashboard'
import Rules from './pages/admin/Rules'
import AuditLog from './pages/admin/AuditLog'

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
        <Route path="/catalog" element={<Navigate to="/shop" replace />} />
        <Route path="/orders" element={<OrderList />} />
        <Route path="/orders/new" element={<OrderNew />} />
        <Route path="/orders/:orderId" element={<OrderDetail />} />
        <Route path="/orders/:orderId/export" element={<OrderExport />} />
        <Route path="/shop/:slug/request" element={<ServiceRequest />} />
        <Route path="/my-services" element={<Resources />} />
        <Route path="/resources" element={<Navigate to="/my-services" replace />} />
        <Route path="/notifications" element={<Notifications />} />
        <Route path="/subscriptions" element={<Subscriptions />} />
        <Route path="/subscriptions/:id" element={<SubscriptionDetail />} />
        <Route
          path="/reviews"
          element={
            <ProtectedRoute requiredRoles={['approver', 'admin']}>
              <Approvals />
            </ProtectedRoute>
          }
        />
        <Route path="/approvals" element={<Navigate to="/reviews" replace />} />
        <Route
          path="/admin"
          element={
            <ProtectedRoute requiredRoles={['admin']}>
              <AdminDashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/rules"
          element={
            <ProtectedRoute requiredRoles={['admin']}>
              <Rules />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/audit-log"
          element={
            <ProtectedRoute requiredRoles={['admin']}>
              <AuditLog />
            </ProtectedRoute>
          }
        />
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
