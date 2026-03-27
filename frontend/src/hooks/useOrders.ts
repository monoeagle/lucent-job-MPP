import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ordersApi, type CreateOrderBody, type AddItemBody, type CreateGroupBody } from '../api/orders'
import { useAuthStore } from '../store/authStore'

export function useOrders(params?: { status?: string; limit?: number; offset?: number }) {
  const token = useAuthStore((s) => s.token)
  return useQuery({
    queryKey: ['orders', params],
    queryFn: () => ordersApi.listOrders(token!, params),
    enabled: !!token,
  })
}

export function useOrder(orderId: string | null) {
  const token = useAuthStore((s) => s.token)
  return useQuery({
    queryKey: ['order', orderId],
    queryFn: () => ordersApi.getOrder(token!, orderId!),
    enabled: !!token && !!orderId,
  })
}

export function useCreateOrder() {
  const token = useAuthStore((s) => s.token)
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: CreateOrderBody) => ordersApi.createOrder(token!, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['orders'] }),
  })
}

export function useAddItem(orderId: string) {
  const token = useAuthStore((s) => s.token)
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: AddItemBody) => ordersApi.addItem(token!, orderId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['order', orderId] }),
  })
}

export function useUpdateItem(orderId: string) {
  const token = useAuthStore((s) => s.token)
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ itemId, parameters }: { itemId: string; parameters: Record<string, unknown> }) =>
      ordersApi.updateItem(token!, orderId, itemId, parameters),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['order', orderId] }),
  })
}

export function useRemoveItem(orderId: string) {
  const token = useAuthStore((s) => s.token)
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (itemId: string) => ordersApi.removeItem(token!, orderId, itemId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['order', orderId] }),
  })
}

export function useValidateOrder(orderId: string) {
  const token = useAuthStore((s) => s.token)
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => ordersApi.validateOrder(token!, orderId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['order', orderId] }),
  })
}

export function useSubmitOrder(orderId: string) {
  const token = useAuthStore((s) => s.token)
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => ordersApi.submitOrder(token!, orderId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['order', orderId] }),
  })
}

export function useDeleteOrder() {
  const token = useAuthStore((s) => s.token)
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (orderId: string) => ordersApi.deleteOrder(token!, orderId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['orders'] }),
  })
}

export function useOrderExport(orderId: string | null) {
  const token = useAuthStore((s) => s.token)
  return useQuery({
    queryKey: ['order-export', orderId],
    queryFn: () => ordersApi.getExport(token!, orderId!),
    enabled: !!token && !!orderId,
  })
}

export function useCreateGroup(orderId: string) {
  const token = useAuthStore((s) => s.token)
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: CreateGroupBody) => ordersApi.createGroup(token!, orderId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['order', orderId] }),
  })
}

export function useDeleteGroup(orderId: string) {
  const token = useAuthStore((s) => s.token)
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (groupId: string) => ordersApi.deleteGroup(token!, orderId, groupId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['order', orderId] }),
  })
}
