/**
 * Features Service - API calls for V1.5 features
 * Wishlists, Coupons, Loyalty, Notifications, Returns, Shipping
 */
import axios from 'axios';
import { config } from '@/config/env';
import type {
  WishlistItem,
  WishlistResponse,
  Coupon,
  CouponValidation,
  CouponValidationResult,
  CouponCreate,
  LoyaltyBalance,
  LoyaltyTransaction,
  LoyaltyRedemption,
  LoyaltyRedemptionResult,
  Notification,
  NotificationList,
  ReturnRequest,
  ReturnRequestCreate,
  ShippingZone,
  ShippingCalculation,
  ShippingCalculationResult,
  AnalyticsSummary,
} from '../types/features';

// Create axios instance with auth
const api = axios.create({
  baseURL: config.api.url,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for auth
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Could dispatch logout action here
      console.error('Unauthorized - token may be expired');
    }
    return Promise.reject(error);
  }
);

// =============================================================================
// WISHLIST SERVICE
// =============================================================================
export const wishlistService = {
  /**
   * Get user's wishlist
   */
  async getWishlist(): Promise<WishlistResponse> {
    const response = await api.get('/wishlist');
    return response.data;
  },

  /**
   * Add product to wishlist
   */
  async addToWishlist(productId: number): Promise<WishlistItem> {
    const response = await api.post(`/wishlist/${productId}`);
    return response.data;
  },

  /**
   * Remove product from wishlist
   */
  async removeFromWishlist(productId: number): Promise<void> {
    await api.delete(`/wishlist/${productId}`);
  },

  /**
   * Check if product is in wishlist
   */
  async checkWishlist(productId: number): Promise<boolean> {
    try {
      const response = await api.get(`/wishlist/${productId}/check`);
      return response.data.in_wishlist;
    } catch {
      return false;
    }
  },

  /**
   * Toggle price notification for wishlist item
   */
  async togglePriceNotification(productId: number, notify: boolean): Promise<WishlistItem> {
    const response = await api.patch(`/wishlist/${productId}/notify`, null, {
      params: { notify },
    });
    return response.data;
  },
};

// =============================================================================
// COUPON SERVICE
// =============================================================================
export const couponService = {
  /**
   * Validate a coupon code
   */
  async validateCoupon(data: CouponValidation): Promise<CouponValidationResult> {
    const response = await api.post('/coupons/validate', data);
    return response.data;
  },

  /**
   * Get user's available coupons
   */
  async getAvailableCoupons(): Promise<Coupon[]> {
    const response = await api.get('/coupons/available');
    return response.data;
  },

  // Admin endpoints
  /**
   * Get all coupons (admin)
   */
  async getAllCoupons(params?: { active_only?: boolean }): Promise<Coupon[]> {
    const response = await api.get('/coupons', { params });
    return response.data;
  },

  /**
   * Create coupon (admin)
   */
  async createCoupon(data: CouponCreate): Promise<Coupon> {
    const response = await api.post('/coupons', data);
    return response.data;
  },

  /**
   * Update coupon (admin)
   */
  async updateCoupon(id: number, data: Partial<CouponCreate>): Promise<Coupon> {
    const response = await api.put(`/coupons/${id}`, data);
    return response.data;
  },

  /**
   * Delete/deactivate coupon (admin)
   */
  async deleteCoupon(id: number): Promise<void> {
    await api.delete(`/coupons/${id}`);
  },
};

// =============================================================================
// LOYALTY SERVICE
// =============================================================================
export const loyaltyService = {
  /**
   * Get user's loyalty balance and recent history
   */
  async getBalance(): Promise<LoyaltyBalance> {
    const response = await api.get('/loyalty/balance');
    return response.data;
  },

  /**
   * Get full loyalty history
   */
  async getHistory(skip = 0, limit = 50): Promise<LoyaltyTransaction[]> {
    const response = await api.get('/loyalty/history', {
      params: { skip, limit },
    });
    return response.data;
  },

  /**
   * Redeem loyalty points
   */
  async redeemPoints(data: LoyaltyRedemption): Promise<LoyaltyRedemptionResult> {
    const response = await api.post('/loyalty/redeem', data);
    return response.data;
  },

  /**
   * Get tier information
   */
  getTierInfo(tier: string): { name: string; minPoints: number; benefits: string[] } {
    const tiers: Record<string, { name: string; minPoints: number; benefits: string[] }> = {
      bronze: {
        name: 'Bronze',
        minPoints: 0,
        benefits: ['1 point per TZS 1,000 spent', 'Birthday bonus'],
      },
      silver: {
        name: 'Silver',
        minPoints: 1000,
        benefits: ['1.5 points per TZS 1,000 spent', 'Birthday bonus', 'Early access to sales'],
      },
      gold: {
        name: 'Gold',
        minPoints: 5000,
        benefits: ['2 points per TZS 1,000 spent', 'Birthday bonus', 'Early access', 'Free shipping on orders over TZS 50,000'],
      },
      platinum: {
        name: 'Platinum',
        minPoints: 10000,
        benefits: ['3 points per TZS 1,000 spent', 'Birthday bonus', 'Early access', 'Free shipping', 'Exclusive offers'],
      },
    };
    return tiers[tier] || tiers.bronze;
  },
};

// =============================================================================
// NOTIFICATION SERVICE
// =============================================================================
export const notificationService = {
  /**
   * Get user's notifications
   */
  async getNotifications(params?: {
    skip?: number;
    limit?: number;
    unread_only?: boolean;
  }): Promise<NotificationList> {
    const response = await api.get('/notifications', { params });
    return response.data;
  },

  /**
   * Get unread notification count
   */
  async getUnreadCount(): Promise<number> {
    const response = await api.get('/notifications/unread-count');
    return response.data.unread_count;
  },

  /**
   * Mark notification as read
   */
  async markAsRead(notificationId: number): Promise<Notification> {
    const response = await api.patch(`/notifications/${notificationId}/read`);
    return response.data;
  },

  /**
   * Mark all notifications as read
   */
  async markAllAsRead(): Promise<void> {
    await api.post('/notifications/mark-all-read');
  },
};

// =============================================================================
// RETURN SERVICE
// =============================================================================
export const returnService = {
  /**
   * Create a return request
   */
  async createReturn(data: ReturnRequestCreate): Promise<ReturnRequest> {
    const response = await api.post('/returns', data);
    return response.data;
  },

  /**
   * Get user's return requests
   */
  async getMyReturns(params?: {
    skip?: number;
    limit?: number;
    status?: string;
  }): Promise<ReturnRequest[]> {
    const response = await api.get('/returns', { params });
    return response.data;
  },

  /**
   * Get return request details
   */
  async getReturn(returnId: number): Promise<ReturnRequest> {
    const response = await api.get(`/returns/${returnId}`);
    return response.data;
  },

  // Admin endpoints
  /**
   * Get all return requests (admin)
   */
  async getAllReturns(params?: {
    skip?: number;
    limit?: number;
    status?: string;
  }): Promise<ReturnRequest[]> {
    const response = await api.get('/returns/admin/all', { params });
    return response.data;
  },

  /**
   * Update return status (admin)
   */
  async updateReturnStatus(
    returnId: number,
    data: { status: string; refund_amount?: number }
  ): Promise<ReturnRequest> {
    const response = await api.patch(`/returns/${returnId}/status`, data);
    return response.data;
  },
};

// =============================================================================
// SHIPPING SERVICE
// =============================================================================
export const shippingService = {
  /**
   * Calculate shipping cost
   */
  async calculateShipping(data: ShippingCalculation): Promise<ShippingCalculationResult> {
    const response = await api.post('/admin/shipping/calculate', data);
    return response.data;
  },

  /**
   * Get available shipping zones for a location
   */
  async getZonesForLocation(country: string, state?: string): Promise<ShippingZone[]> {
    const response = await api.get('/admin/shipping/zones', {
      params: { country, state, active_only: true },
    });
    return response.data;
  },

  // Admin endpoints
  /**
   * Get all shipping zones (admin)
   */
  async getAllZones(): Promise<ShippingZone[]> {
    const response = await api.get('/admin/shipping/zones');
    return response.data;
  },

  /**
   * Create shipping zone (admin)
   */
  async createZone(data: Omit<ShippingZone, 'id'>): Promise<ShippingZone> {
    const response = await api.post('/admin/shipping/zones', data);
    return response.data;
  },

  /**
   * Update shipping zone (admin)
   */
  async updateZone(id: number, data: Partial<ShippingZone>): Promise<ShippingZone> {
    const response = await api.put(`/admin/shipping/zones/${id}`, data);
    return response.data;
  },

  /**
   * Delete shipping zone (admin)
   */
  async deleteZone(id: number): Promise<void> {
    await api.delete(`/admin/shipping/zones/${id}`);
  },
};

// =============================================================================
// ANALYTICS SERVICE (Admin)
// =============================================================================
export const analyticsService = {
  /**
   * Get dashboard summary
   */
  async getDashboard(): Promise<AnalyticsSummary> {
    const response = await api.get('/admin/analytics/dashboard');
    return response.data;
  },

  /**
   * Get revenue data over time
   */
  async getRevenue(params?: {
    start_date?: string;
    end_date?: string;
    group_by?: 'day' | 'week' | 'month';
  }): Promise<Array<{ date: string; revenue: number; orders: number }>> {
    const response = await api.get('/admin/analytics/revenue', { params });
    return response.data;
  },

  /**
   * Get top products
   */
  async getTopProducts(params?: {
    limit?: number;
    period?: 'week' | 'month' | 'year';
  }): Promise<Array<{ id: number; name: string; sales: number; revenue: number }>> {
    const response = await api.get('/admin/analytics/top-products', { params });
    return response.data;
  },

  /**
   * Track product view (public)
   */
  async trackProductView(data: {
    product_id: number;
    session_id?: string;
    duration_seconds?: number;
    device_type?: string;
    referrer?: string;
  }): Promise<void> {
    await api.post('/admin/analytics/track-view', data);
  },
};

// Export all services
export const featuresService = {
  wishlist: wishlistService,
  coupon: couponService,
  loyalty: loyaltyService,
  notification: notificationService,
  return: returnService,
  shipping: shippingService,
  analytics: analyticsService,
};

export default featuresService;
