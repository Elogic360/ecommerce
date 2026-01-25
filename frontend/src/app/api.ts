import axios from 'axios';
import { useStore } from './store';
import { config, getImageUrl as getImageUrlFromConfig } from '@/config/env';

// Re-export getImageUrl from centralized config
export const getImageUrl = getImageUrlFromConfig;

const api = axios.create({
  baseURL: config.api.url,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
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
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      // Clear token in app store so UI can react immediately
      try {
        useStore.getState().setToken(null);
      } catch (e) {
        // ignore if store isn't available
      }
      // window.location.href = '/login'; // Let the app handle redirection
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  register: (data: {
    email: string;
    username: string;
    password: string;
    confirm_password: string;
    full_name?: string;
    phone?: string
  }) => api.post('/auth/register', data),

  login: (data: { email: string; password: string }) => {
    // FastAPI OAuth2 uses form data for login by default with OAuth2PasswordRequestForm
    const formData = new FormData();
    formData.append('username', data.email);
    formData.append('password', data.password);
    return api.post('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    });
  },

  googleLogin: (token: string) => api.post('/auth/login/google', { token }),

  me: () => api.get('/auth/me'),

  updateProfile: (data: { username?: string; full_name?: string; phone?: string }) =>
    api.patch('/auth/me', data),

  changePassword: (data: { current_password: string; new_password: string; confirm_password: string }) =>
    api.post('/auth/password/change', data),
};

// Products API
export const productsAPI = {
  getAll: (params?: {
    skip?: number;
    limit?: number;
    search?: string;
    category_id?: number;
    min_price?: number;
    max_price?: number;
    sort_by?: string;
    sort_order?: string;
    is_featured?: boolean;
  }) => api.get('/products', { params }),

  getById: (id: number) => api.get(`/products/${id}`),

  getReviews: (id: number, params?: { skip?: number; limit?: number }) =>
    api.get(`/products/${id}/reviews`, { params }),

  createReview: (id: number, data: { rating: number; title?: string; comment?: string }) =>
    api.post(`/products/${id}/reviews`, data),
};

// Admin Products API
export const adminProductsAPI = {
  getAll: (params?: { skip?: number; limit?: number; search?: string }) =>
    api.get('/admin/products', { params }),

  create: (data: any) => api.post('/admin/products', data),

  update: (id: number, data: any) => api.put(`/admin/products/${id}`, data),

  delete: (id: number) => api.delete(`/admin/products/${id}`),

  uploadImage: (id: number, file: File, isPrimary: boolean = false) => {
    const formData = new FormData();
    formData.append('file', file);
    if (isPrimary) {
      formData.append('is_primary', 'true');
    }
    return api.post(`/admin/products/${id}/images`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  deleteImage: (imageId: number) => api.delete(`/admin/products/images/${imageId}`),
};

// Cart API
export const cartAPI = {
  get: () => api.get('/cart/smart'),

  add: (data: { product_id: number; variation_id?: number; quantity: number }) =>
    api.post('/cart/smart/items', data),

  update: (id: number, data: { quantity: number }) => api.put(`/cart/smart/items/${id}`, data),

  remove: (id: number) => api.delete(`/cart/smart/items/${id}`),

  clear: () => api.delete('/cart'),
};

// Orders API
export const ordersAPI = {
  create: (data: {
    address_id: number;
    payment_method: string;
    notes?: string;
    items: Array<{ product_id: number; variation_id?: number; quantity: number }>;
  }) => api.post('/orders', data),

  createGuest: (data: {
    guest_email: string;
    guest_name: string;
    guest_phone: string;
    address_line_1: string;
    address_line_2?: string;
    city: string;
    state: string;
    postal_code: string;
    country: string;
    payment_method: string;
    notes?: string;
    items: Array<{ product_id: number; variation_id?: number; quantity: number }>;
  }) => api.post('/orders/guest', data),

  trackGuest: (orderNumber: string, email: string) =>
    api.get('/orders/guest/track', { params: { order_number: orderNumber, email } }),

  getAll: (params?: { skip?: number; limit?: number }) => api.get('/orders', { params }),

  getById: (id: number) => api.get(`/orders/${id}`),
};

// Admin Orders API
export const adminOrdersAPI = {
  getAll: (params?: { skip?: number; limit?: number; status?: string }) =>
    api.get('/admin/orders', { params }),

  update: (id: number, data: { status?: string; payment_status?: string; notes?: string }) =>
    api.put(`/admin/orders/${id}`, data),

  cancel: (id: number) => api.delete(`/admin/orders/${id}`),
};

// Categories API
export const categoriesAPI = {
  getAll: () => api.get('/categories'),

  getById: (id: number) => api.get(`/categories/${id}`),
};

// Admin Dashboard API
export const adminDashboardAPI = {
  getStats: () => api.get('/admin/dashboard/stats'),
  getSales: (params?: { period?: string; days?: number }) => api.get('/admin/dashboard/sales', { params }),
  getTopProducts: (params?: { limit?: number }) => api.get('/admin/dashboard/top-products', { params }),
  getCategorySales: () => api.get('/admin/dashboard/category-sales'),
  getRecentOrders: (params?: { limit?: number }) => api.get('/admin/dashboard/recent-orders', { params }),
  getLowStock: (params?: { limit?: number }) => api.get('/admin/dashboard/low-stock', { params }),
};

// Admin Users API
export const adminUsersAPI = {
  getAll: (params?: { skip?: number; limit?: number; search?: string }) =>
    api.get('/admin/users', { params }),

  getById: (id: number) => api.get(`/admin/users/${id}`),

  update: (id: number, data: any) => api.put(`/admin/users/${id}`, data),

  delete: (id: number) => api.delete(`/admin/users/${id}`),
};

// Admin Inventory API
export const adminInventoryAPI = {
  getAll: (params?: { skip?: number; limit?: number }) =>
    api.get('/admin/inventory', { params }),

  getLogs: (params?: { product_id?: number; skip?: number; limit?: number }) =>
    api.get('/admin/inventory/logs', { params }),

  adjust: (data: { product_id: number; quantity_change: number; reason: string }) =>
    api.post('/admin/inventory/adjust', data),

  getLowStock: (params?: { threshold?: number; skip?: number; limit?: number }) =>
    api.get('/admin/inventory/low-stock', { params }),
};

// Admin Categories API
export const adminCategoriesAPI = {
  getAll: () => api.get('/admin/categories'),

  create: (data: { name: string; description?: string; parent_id?: number }) =>
    api.post('/admin/categories', data),

  update: (id: number, data: { name?: string; description?: string; parent_id?: number }) =>
    api.put(`/admin/categories/${id}`, data),

  delete: (id: number) => api.delete(`/admin/categories/${id}`),
};

// Types
export type Customer = {
  id: number;
  email: string;
  username: string;
  name: string;
  phone?: string;
  is_active: boolean;
  role: string;
  created_at: string;
};

export type InventoryItem = {
  id: number;
  product_id: number;
  product_name: string;
  stock_quantity: number;
  reserved_stock?: number;
  available_stock?: number;
  low_stock?: boolean;
  last_updated: string;
};

export type InventoryLog = {
  id: number;
  product_id: number;
  action: 'add' | 'remove' | 'adjust';
  quantity: number;
  reason?: string;
  new_stock?: number;
  created_at: string;
};

export type ProductCreate = {
  name: string;
  description?: string;
  short_description?: string;
  price: number;
  original_price?: number;
  sale_price?: number;
  stock: number;
  sku?: string;
  brand?: string;
  is_active?: boolean;
  is_featured?: boolean;
  is_new?: boolean;
  is_bestseller?: boolean;
  category_ids?: number[];
  images?: File[];
};

export type ProductUpdate = Partial<ProductCreate> & { id: number };

// Aliases for backward compatibility
export const adminApi = adminUsersAPI;

export default api;
