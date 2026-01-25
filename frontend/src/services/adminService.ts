/**
 * Admin Service - Comprehensive API service for admin operations
 */
import axios from 'axios';
import { config } from '@/config/env';

const adminApi = axios.create({
  baseURL: config.api.url,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
adminApi.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
adminApi.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// =============================================================================
// TYPES
// =============================================================================

export interface AdminStats {
  total_revenue: number;
  total_orders: number;
  total_products: number;
  total_users: number;
  pending_orders: number;
  low_stock_count: number;
  revenue_change: number;
  orders_change: number;
}

export interface SalesData {
  date: string;
  revenue: number;
  orders: number;
}

export interface TopProduct {
  id: number;
  name: string;
  sales_count: number;
  revenue: number;
  image_url?: string;
}

export interface CategorySales {
  category: string;
  sales: number;
  percentage: number;
}

export interface AdminProduct {
  id: number;
  name: string;
  slug: string;
  description?: string;
  sku: string;
  price: number;
  original_price?: number;
  cost_price?: number;
  stock: number;
  low_stock_threshold: number;
  is_active: boolean;
  is_featured: boolean;
  category_id?: number;
  category?: { id: number; name: string };
  brand?: string;
  weight?: number;
  dimensions?: string;
  primary_image?: string;
  images: Array<{
    id: number;
    url: string;
    alt_text?: string;
    is_primary: boolean;
    sort_order: number;
  }>;
  rating_average: number;
  rating_count: number;
  sales_count: number;
  created_at: string;
  updated_at: string;
}

export interface AdminOrder {
  id: number;
  user_id?: number;
  user?: {
    id: number;
    email: string;
    username: string;
    full_name?: string;
    phone?: string;
  };
  total_amount: number;
  subtotal: number;
  shipping_cost: number;
  tax_amount: number;
  discount_amount: number;
  status: 'pending' | 'confirmed' | 'processing' | 'shipped' | 'delivered' | 'cancelled' | 'refunded';
  payment_status: 'pending' | 'paid' | 'failed' | 'refunded';
  payment_method?: string;
  shipping_address: {
    full_name: string;
    street: string;
    city: string;
    state: string;
    zip_code: string;
    country: string;
    phone?: string;
  };
  billing_address?: {
    full_name: string;
    street: string;
    city: string;
    state: string;
    zip_code: string;
    country: string;
  };
  items: Array<{
    id: number;
    product_id: number;
    product_name: string;
    product_sku: string;
    product_image?: string;
    quantity: number;
    unit_price: number;
    total: number;
    variation?: string;
  }>;
  notes?: string;
  tracking_number?: string;
  created_at: string;
  updated_at: string;
}

export interface AdminUser {
  id: number;
  email: string;
  username: string;
  full_name?: string;
  phone?: string;
  role: 'customer' | 'admin' | 'staff';
  is_active: boolean;
  is_verified: boolean;
  avatar_url?: string;
  orders_count: number;
  total_spent: number;
  last_login?: string;
  created_at: string;
  updated_at: string;
}

export interface AdminCategory {
  id: number;
  name: string;
  slug: string;
  description?: string;
  image_url?: string;
  parent_id?: number;
  product_count: number;
  is_active: boolean;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ProductFilters {
  page?: number;
  page_size?: number;
  search?: string;
  category_id?: number;
  is_active?: boolean;
  is_featured?: boolean;
  low_stock?: boolean;
  sort_by?: 'name' | 'price' | 'stock' | 'created_at' | 'sales_count';
  sort_order?: 'asc' | 'desc';
}

export interface OrderFilters {
  page?: number;
  page_size?: number;
  search?: string;
  status?: string;
  payment_status?: string;
  date_from?: string;
  date_to?: string;
  sort_by?: 'created_at' | 'total_amount';
  sort_order?: 'asc' | 'desc';
}

export interface UserFilters {
  page?: number;
  page_size?: number;
  search?: string;
  role?: string;
  is_active?: boolean;
  sort_by?: 'created_at' | 'orders_count' | 'total_spent';
  sort_order?: 'asc' | 'desc';
}

// =============================================================================
// DASHBOARD API
// =============================================================================

export const dashboardAPI = {
  getStats: async (): Promise<AdminStats> => {
    const response = await adminApi.get('/admin/dashboard/stats');
    return response.data;
  },

  getSalesData: async (period: 'daily' | 'weekly' | 'monthly' = 'daily', days: number = 30): Promise<SalesData[]> => {
    const response = await adminApi.get('/admin/dashboard/sales', { params: { period, days } });
    return response.data;
  },

  getTopProducts: async (limit: number = 10): Promise<TopProduct[]> => {
    const response = await adminApi.get('/admin/dashboard/top-products', { params: { limit } });
    return response.data;
  },

  getCategorySales: async (): Promise<CategorySales[]> => {
    const response = await adminApi.get('/admin/dashboard/category-sales');
    return response.data;
  },

  getRecentOrders: async (limit: number = 5): Promise<AdminOrder[]> => {
    const response = await adminApi.get('/admin/dashboard/recent-orders', { params: { limit } });
    return response.data;
  },

  getLowStockProducts: async (limit: number = 10): Promise<AdminProduct[]> => {
    const response = await adminApi.get('/admin/dashboard/low-stock', { params: { limit } });
    return response.data;
  },
};

// =============================================================================
// PRODUCTS API
// =============================================================================

export const productsAdminAPI = {
  getAll: async (filters: ProductFilters = {}): Promise<PaginatedResponse<AdminProduct>> => {
    const response = await adminApi.get('/admin/products', { params: filters });
    return response.data;
  },

  getById: async (id: number): Promise<AdminProduct> => {
    const response = await adminApi.get(`/admin/products/${id}`);
    return response.data;
  },

  create: async (data: Partial<AdminProduct>): Promise<AdminProduct> => {
    const response = await adminApi.post('/admin/products', data);
    return response.data;
  },

  createSimple: async (data: { name: string; category_id?: number | null; price: number; new_price?: number | null }): Promise<AdminProduct> => {
    const response = await adminApi.post('/admin/products/simple', data);
    return response.data;
  },

  update: async (id: number, data: Partial<AdminProduct>): Promise<AdminProduct> => {
    const response = await adminApi.put(`/admin/products/${id}`, data);
    return response.data;
  },

  delete: async (id: number): Promise<void> => {
    await adminApi.delete(`/admin/products/${id}`);
  },

  bulkDelete: async (ids: number[]): Promise<void> => {
    await adminApi.post('/admin/products/bulk-delete', { ids });
  },

  bulkUpdate: async (ids: number[], data: Partial<AdminProduct>): Promise<void> => {
    await adminApi.post('/admin/products/bulk-update', { ids, data });
  },

  uploadImage: async (productId: number, file: File, isPrimary: boolean = false): Promise<{ id: number; url: string }> => {
    const formData = new FormData();
    formData.append('file', file);
    if (isPrimary) {
      formData.append('is_primary', 'true');
    }
    const response = await adminApi.post(`/admin/products/${productId}/images`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    // Handle response - backend returns { images: [...] }
    if (response.data.images && response.data.images.length > 0) {
      const img = response.data.images[0];
      return { id: img.id, url: img.url };
    }
    return response.data;
  },

  deleteImage: async (imageId: number): Promise<void> => {
    await adminApi.delete(`/admin/products/images/${imageId}`);
  },

  reorderImages: async (productId: number, imageIds: number[]): Promise<void> => {
    await adminApi.put(`/admin/products/${productId}/images/reorder`, { image_ids: imageIds });
  },

  updateStock: async (id: number, quantity: number, reason?: string): Promise<AdminProduct> => {
    const response = await adminApi.post(`/admin/products/${id}/stock`, { quantity, reason });
    return response.data;
  },

  exportCSV: async (filters: ProductFilters = {}): Promise<Blob> => {
    const response = await adminApi.get('/admin/products/export', {
      params: filters,
      responseType: 'blob',
    });
    return response.data;
  },
};

// =============================================================================
// ORDERS API
// =============================================================================

export const ordersAdminAPI = {
  getAll: async (filters: OrderFilters = {}): Promise<PaginatedResponse<AdminOrder>> => {
    const response = await adminApi.get('/admin/orders', { params: filters });
    return response.data;
  },

  getById: async (id: number): Promise<AdminOrder> => {
    const response = await adminApi.get(`/admin/orders/${id}`);
    return response.data;
  },

  updateStatus: async (id: number, status: string, notes?: string): Promise<AdminOrder> => {
    const response = await adminApi.put(`/admin/orders/${id}/status`, { status, notes });
    return response.data;
  },

  updatePaymentStatus: async (id: number, payment_status: string): Promise<AdminOrder> => {
    const response = await adminApi.put(`/admin/orders/${id}/payment-status`, { payment_status });
    return response.data;
  },

  addTrackingNumber: async (id: number, tracking_number: string): Promise<AdminOrder> => {
    const response = await adminApi.put(`/admin/orders/${id}/tracking`, { tracking_number });
    return response.data;
  },

  addNote: async (id: number, note: string): Promise<AdminOrder> => {
    const response = await adminApi.post(`/admin/orders/${id}/notes`, { note });
    return response.data;
  },

  cancel: async (id: number, reason?: string): Promise<AdminOrder> => {
    const response = await adminApi.post(`/admin/orders/${id}/cancel`, { reason });
    return response.data;
  },

  refund: async (id: number, amount?: number, reason?: string): Promise<AdminOrder> => {
    const response = await adminApi.post(`/admin/orders/${id}/refund`, { amount, reason });
    return response.data;
  },

  generateInvoice: async (id: number): Promise<Blob> => {
    const response = await adminApi.get(`/admin/orders/${id}/invoice`, {
      responseType: 'blob',
    });
    return response.data;
  },

  exportCSV: async (filters: OrderFilters = {}): Promise<Blob> => {
    const response = await adminApi.get('/admin/orders/export', {
      params: filters,
      responseType: 'blob',
    });
    return response.data;
  },
};

// =============================================================================
// USERS API
// =============================================================================

export const usersAdminAPI = {
  getAll: async (filters: UserFilters = {}): Promise<PaginatedResponse<AdminUser>> => {
    const response = await adminApi.get('/admin/users', { params: filters });
    return response.data;
  },

  getById: async (id: number): Promise<AdminUser> => {
    const response = await adminApi.get(`/admin/users/${id}`);
    return response.data;
  },

  update: async (id: number, data: Partial<AdminUser>): Promise<AdminUser> => {
    const response = await adminApi.put(`/admin/users/${id}`, data);
    return response.data;
  },

  updateRole: async (id: number, role: string): Promise<AdminUser> => {
    const response = await adminApi.put(`/admin/users/${id}/role`, { role });
    return response.data;
  },

  activate: async (id: number): Promise<AdminUser> => {
    const response = await adminApi.post(`/admin/users/${id}/activate`);
    return response.data;
  },

  deactivate: async (id: number): Promise<AdminUser> => {
    const response = await adminApi.post(`/admin/users/${id}/deactivate`);
    return response.data;
  },

  delete: async (id: number): Promise<void> => {
    await adminApi.delete(`/admin/users/${id}`);
  },

  getOrders: async (userId: number): Promise<AdminOrder[]> => {
    const response = await adminApi.get(`/admin/users/${userId}/orders`);
    return response.data;
  },

  exportCSV: async (filters: UserFilters = {}): Promise<Blob> => {
    const response = await adminApi.get('/admin/users/export', {
      params: filters,
      responseType: 'blob',
    });
    return response.data;
  },
};

// =============================================================================
// CATEGORIES API
// =============================================================================

export const categoriesAdminAPI = {
  getAll: async (): Promise<AdminCategory[]> => {
    const response = await adminApi.get('/admin/categories');
    return response.data;
  },

  getById: async (id: number): Promise<AdminCategory> => {
    const response = await adminApi.get(`/admin/categories/${id}`);
    return response.data;
  },

  create: async (data: Partial<AdminCategory>): Promise<AdminCategory> => {
    const response = await adminApi.post('/admin/categories', data);
    return response.data;
  },

  update: async (id: number, data: Partial<AdminCategory>): Promise<AdminCategory> => {
    const response = await adminApi.put(`/admin/categories/${id}`, data);
    return response.data;
  },

  delete: async (id: number): Promise<void> => {
    await adminApi.delete(`/admin/categories/${id}`);
  },
};

// =============================================================================
// ANALYTICS API
// =============================================================================

export const analyticsAPI = {
  getSalesReport: async (dateFrom: string, dateTo: string): Promise<{
    total_revenue: number;
    total_orders: number;
    average_order_value: number;
    daily_sales: SalesData[];
  }> => {
    const response = await adminApi.get('/admin/analytics/sales', {
      params: { date_from: dateFrom, date_to: dateTo },
    });
    return response.data;
  },

  getProductsReport: async (): Promise<{
    top_sellers: TopProduct[];
    low_performers: TopProduct[];
    category_distribution: CategorySales[];
  }> => {
    const response = await adminApi.get('/admin/analytics/products');
    return response.data;
  },

  getCustomersReport: async (): Promise<{
    new_customers: number;
    returning_customers: number;
    customer_lifetime_value: number;
    top_customers: Array<{
      id: number;
      name: string;
      email: string;
      orders_count: number;
      total_spent: number;
    }>;
  }> => {
    const response = await adminApi.get('/admin/analytics/customers');
    return response.data;
  },

  exportReport: async (type: 'sales' | 'products' | 'customers', dateFrom?: string, dateTo?: string): Promise<Blob> => {
    const response = await adminApi.get(`/admin/analytics/export/${type}`, {
      params: { date_from: dateFrom, date_to: dateTo },
      responseType: 'blob',
    });
    return response.data;
  },
};

// =============================================================================
// INVENTORY API
// =============================================================================

export const inventoryAPI = {
  getLogs: async (productId?: number, page: number = 1, pageSize: number = 20): Promise<PaginatedResponse<{
    id: number;
    product_id: number;
    product_name: string;
    quantity_before: number;
    quantity_after: number;
    change: number;
    reason: string;
    created_by: string;
    created_at: string;
  }>> => {
    const response = await adminApi.get('/admin/inventory/logs', {
      params: { product_id: productId, page, page_size: pageSize },
    });
    return response.data;
  },

  adjustStock: async (productId: number, change: number, reason: string): Promise<void> => {
    await adminApi.post('/admin/inventory/adjust', {
      product_id: productId,
      quantity_change: change,
      reason,
    });
  },

  getLowStock: async (threshold?: number): Promise<AdminProduct[]> => {
    const response = await adminApi.get('/admin/inventory/low-stock', {
      params: { threshold },
    });
    return response.data;
  },
};

// =============================================================================
// UTILITY FUNCTIONS
// =============================================================================

export const downloadBlob = (blob: Blob, filename: string) => {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};

export const formatCurrency = (amount: number): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(amount);
};

export const formatDate = (date: string): string => {
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(new Date(date));
};

export const formatDateTime = (date: string): string => {
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(date));
};

// =============================================================================
// ADMIN SERVICE NAMESPACE (for convenience)
// =============================================================================

export const adminService = {
  dashboardAPI,
  productsAPI: productsAdminAPI,
  ordersAPI: ordersAdminAPI,
  usersAPI: usersAdminAPI,
  categoriesAPI: categoriesAdminAPI,
  analyticsAPI,
  inventoryAPI,
};

export default adminApi;
