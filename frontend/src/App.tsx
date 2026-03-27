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
        <Route index element={<Navigate to="/orders" replace />} />
        <Route path="/catalog" element={<Catalog />} />
        <Route path="/orders" element={<OrderList />} />
        <Route path="/orders/new" element={<OrderNew />} />
        <Route path="/orders/:orderId" element={<OrderDetail />} />
        <Route path="/orders/:orderId/export" element={<OrderExport />} />
        <Route path="/resources" element={<Dashboard />} />
        <Route path="/approvals" element={<Dashboard />} />
        <Route path="/admin/*" element={<Dashboard />} />
      </Route>
      <Route path="*" element={<Navigate to="/orders" replace />} />
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
