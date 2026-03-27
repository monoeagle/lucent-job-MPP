import { useQuery } from '@tanstack/react-query'
import { ordersApi } from '../api/orders'
import { useAuthStore } from '../store/authStore'

const POLLING_STATUSES = ['submitted', 'pending_approval', 'provisioning']

export function useOrderStatus(orderId: string | null, currentStatus: string | null) {
  const token = useAuthStore((s) => s.token)
  const shouldPoll = !!currentStatus && POLLING_STATUSES.includes(currentStatus)

  return useQuery({
    queryKey: ['order-status', orderId],
    queryFn: () => ordersApi.getStatus(token!, orderId!),
    enabled: !!token && !!orderId && shouldPoll,
    refetchInterval: shouldPoll ? 10_000 : false,
  })
}
