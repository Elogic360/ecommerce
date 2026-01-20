import type { Order, OrderCreate, Payment, Product, CustomerInfo } from './types'

const API_BASE = (import.meta as any).env?.VITE_API_BASE ?? 'http://localhost:8000/api'

// Admin token for protected endpoints
let adminToken: string | null = localStorage.getItem('admin_token')

export function setAdminToken(token: string | null) {
  adminToken = token
  if (token) {
    localStorage.setItem('admin_token', token)
  } else {
    localStorage.removeItem('admin_token')
  }
}

export function getAdminToken(): string | null {
  return adminToken
}

async function request<T>(path: string, init?: RequestInit, requiresAuth = false): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(init?.headers as Record<string, string> ?? {})
  }

  if (requiresAuth && adminToken) {
    headers['Authorization'] = `Bearer ${adminToken}`
  }

  const res = await fetch(`${API_BASE}${path}`, {
    headers,
    ...init
  })

  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `Request failed: ${res.status}`)
  }

  // Handle 204 No Content
  if (res.status === 204) {
    return null as T
  }

  return (await res.json()) as T
}

// ============ PUBLIC API ============

export const api = {
  health: () => request<{ status: string }>('/health'),

  // Products (public)
  listProducts: (params?: { q?: string; category?: string }) => {
    const sp = new URLSearchParams()
    if (params?.q) sp.set('q', params.q)
    if (params?.category) sp.set('category', params.category)
    const qs = sp.toString()
    return request<Product[]>(`/products/${qs ? `?${qs}` : ''}`)
  },

  getProduct: (id: number) => request<Product>(`/products/${id}`),

  // Orders (public checkout)
  createOrder: (payload: OrderCreate) =>
    request<Order>('/orders/', { method: 'POST', body: JSON.stringify(payload) }),

  getOrder: (id: number) => request<Order>(`/orders/${id}`),

  // Payment verification (public)
  verifyPayment: (payload: { order_id: number; success: boolean; provider_ref?: string }) =>
    request<Payment>('/payments/verify', { method: 'POST', body: JSON.stringify(payload) })
}

// ============ ADMIN API ============

export type Customer = {
  id: number
  name: string
  email: string
  phone: string
}

export type InventoryItem = {
  product_id: number
  name: string
  stock_quantity: number
  is_active: boolean
  low_stock: boolean
}

export type InventoryLog = {
  id: number
  product_id: number
  change_quantity: number
  new_stock: number | null
  reason: string
  created_at: string | null
}

export type ProductCreate = {
  name: string
  description?: string
  image_url?: string
  price: number
  stock_quantity: number
  is_active?: boolean
}

export type ProductUpdate = Partial<ProductCreate>

export const adminApi = {
  // Admin auth
  verifyAdmin: () => request<{ role: string; ok: boolean }>('/admin/me', {}, true),

  // Products CRUD
  listProducts: (includeInactive = true) =>
    request<Product[]>(`/products/?include_inactive=${includeInactive}`, {}, true),

  createProduct: (data: ProductCreate) =>
    request<Product>('/products/', { method: 'POST', body: JSON.stringify(data) }, true),

  updateProduct: (id: number, data: ProductUpdate) =>
    request<Product>(`/products/${id}`, { method: 'PATCH', body: JSON.stringify(data) }, true),

  deleteProduct: (id: number) =>
    request<null>(`/products/${id}`, { method: 'DELETE' }, true),

  // Orders
  listOrders: () => request<Order[]>('/orders/', {}, true),

  updateOrderStatus: (id: number, status: { order_status: string; payment_status?: string }) =>
    request<Order>(`/orders/${id}/status`, { method: 'PATCH', body: JSON.stringify(status) }, true),

  // Customers
  listCustomers: () => request<Customer[]>('/customers/', {}, true),

  getCustomer: (id: number) => request<Customer>(`/customers/${id}`, {}, true),

  // Inventory
  listInventory: () => request<InventoryItem[]>('/inventory/', {}, true),

  getLowStock: (threshold = 5) =>
    request<InventoryItem[]>(`/inventory/low-stock?threshold=${threshold}`, {}, true),

  adjustInventory: (data: { product_id: number; change_quantity: number; reason?: string }) =>
    request<{ success: boolean; product_id: number; new_stock: number; change: number }>(
      '/inventory/adjust',
      { method: 'POST', body: JSON.stringify(data) },
      true
    ),

  getInventoryLogs: (productId?: number, limit = 50) => {
    const params = new URLSearchParams()
    if (productId) params.set('product_id', String(productId))
    params.set('limit', String(limit))
    return request<InventoryLog[]>(`/inventory/logs?${params}`, {}, true)
  },

  // Payments
  listPayments: () => request<Payment[]>('/payments/', {}, true)
}