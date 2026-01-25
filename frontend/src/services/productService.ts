/**
 * Product Service - API calls for product-related operations
 */
import axios from 'axios';
import { config, getImageUrl as getImageUrlFromConfig } from '@/config/env';
import type {
  Product,
  ProductSummary,
  ProductListResponse,
  ProductDetailResponse,
  ProductQueryParams,
  Category,
  ProductReview,
  CreateReviewPayload,
  ReviewsResponse,
} from '../types/product';

// Create axios instance
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

// =============================================================================
// UTILITY FUNCTIONS
// =============================================================================

/**
 * Get full image URL from relative path
 */
export const getImageUrl = getImageUrlFromConfig;

/**
 * Format price to TZS currency
 */
export const formatPrice = (price: number): string => {
  return new Intl.NumberFormat('en-TZ', {
    style: 'currency',
    currency: 'TZS',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(price);
};

/**
 * Calculate discount percentage
 */
export const calculateDiscount = (price: number, originalPrice?: number): number => {
  if (!originalPrice || originalPrice <= price) return 0;
  return Math.round(((originalPrice - price) / originalPrice) * 100);
};

// =============================================================================
// PRODUCT API CALLS
// =============================================================================

export const productService = {
  /**
   * Get paginated list of products with filters
   */
  async getProducts(params: Partial<ProductQueryParams> = {}): Promise<ProductListResponse> {
    const queryParams = {
      skip: ((params.page || 1) - 1) * (params.page_size || 12),
      limit: params.page_size || 12,
      search: params.search || undefined,
      category_id: params.category_id || undefined,
      min_price: params.min_price || undefined,
      max_price: params.max_price || undefined,
      in_stock: params.in_stock_only || undefined,
      is_featured: params.is_featured || undefined,
      sort_by: params.sort_by ? mapSortToApi(params.sort_by) : undefined,
      sort_order: params.sort_by ? getSortOrder(params.sort_by) : undefined,
    };

    // Remove undefined values
    const cleanParams = Object.fromEntries(
      Object.entries(queryParams).filter(([, v]) => v !== undefined)
    );

    const response = await api.get('/products', { params: cleanParams });

    // Transform response to match our interface
    const data = response.data;
    const items = Array.isArray(data) ? data : data.items || [];
    const total = data.total || items.length;
    const pageSize = params.page_size || 12;

    return {
      items: items.map(transformProductSummary),
      total,
      page: params.page || 1,
      page_size: pageSize,
      total_pages: Math.ceil(total / pageSize),
    };
  },

  /**
   * Get single product by ID
   */
  async getProductById(id: number): Promise<Product> {
    const response = await api.get(`/products/${id}`);
    return transformProduct(response.data);
  },

  /**
   * Get single product by slug
   */
  async getProductBySlug(slug: string): Promise<Product> {
    const response = await api.get(`/products/slug/${slug}`);
    return transformProduct(response.data);
  },

  /**
   * Get product with related products and reviews
   */
  async getProductDetail(id: number): Promise<ProductDetailResponse> {
    const [product, reviews] = await Promise.all([
      this.getProductById(id),
      this.getProductReviews(id, 1, 5),
    ]);

    // Get related products (same category)
    let relatedProducts: ProductSummary[] = [];
    if (product.category_id) {
      const related = await this.getProducts({
        category_id: product.category_id,
        page_size: 4,
      });
      relatedProducts = related.items.filter((p) => p.id !== product.id).slice(0, 4);
    }

    return {
      product,
      related_products: relatedProducts,
      recent_reviews: reviews.items,
    };
  },

  /**
   * Get featured products
   */
  async getFeaturedProducts(limit: number = 8): Promise<ProductSummary[]> {
    const response = await this.getProducts({
      is_featured: true,
      page_size: limit,
    });
    return response.items;
  },

  /**
   * Search products
   */
  async searchProducts(query: string, limit: number = 10): Promise<ProductSummary[]> {
    const response = await this.getProducts({
      search: query,
      page_size: limit,
    });
    return response.items;
  },

  /**
   * Get product reviews
   */
  async getProductReviews(
    productId: number,
    page: number = 1,
    pageSize: number = 10
  ): Promise<ReviewsResponse> {
    try {
      const response = await api.get(`/products/${productId}/reviews`, {
        params: { skip: (page - 1) * pageSize, limit: pageSize },
      });

      const items = Array.isArray(response.data) ? response.data : response.data.items || [];

      return {
        items: items.map(transformReview),
        total: response.data.total || items.length,
        average_rating: response.data.average_rating || 0,
        rating_distribution: response.data.rating_distribution || {},
      };
    } catch {
      return {
        items: [],
        total: 0,
        average_rating: 0,
        rating_distribution: {},
      };
    }
  },

  /**
   * Create a product review
   */
  async createReview(productId: number, review: CreateReviewPayload): Promise<ProductReview> {
    const response = await api.post(`/products/${productId}/reviews`, review);
    return transformReview(response.data);
  },
};

// =============================================================================
// CATEGORY API CALLS
// =============================================================================

export const categoryService = {
  /**
   * Get all categories
   */
  async getCategories(): Promise<Category[]> {
    const response = await api.get('/categories');
    const data = Array.isArray(response.data) ? response.data : response.data.items || [];
    return data.map(transformCategory);
  },

  /**
   * Get category by ID
   */
  async getCategoryById(id: number): Promise<Category> {
    const response = await api.get(`/categories/${id}`);
    return transformCategory(response.data);
  },

  /**
   * Get category by slug
   */
  async getCategoryBySlug(slug: string): Promise<Category> {
    const response = await api.get(`/categories/slug/${slug}`);
    return transformCategory(response.data);
  },
};

// =============================================================================
// DATA TRANSFORMERS
// =============================================================================

function transformProductSummary(data: any): ProductSummary {
  return {
    id: data.id,
    name: data.name,
    slug: data.slug || `product-${data.id}`,
    price: Number(data.price) || 0,
    original_price: data.original_price ? Number(data.original_price) : undefined,
    stock: data.stock ?? data.stock_quantity ?? 0,
    is_active: data.is_active ?? true,
    is_featured: data.is_featured ?? false,
    category: data.category?.name || data.category || undefined,
    primary_image: data.primary_image || data.image_url,
    thumbnail: data.thumbnail || data.primary_image || data.image_url,
    rating_average: data.rating_average ?? data.rating ?? 0,
    rating_count: data.rating_count ?? data.review_count ?? 0,
  };
}

function transformProduct(data: any): Product {
  return {
    id: data.id,
    name: data.name,
    slug: data.slug || `product-${data.id}`,
    description: data.description,
    short_description: data.short_description,
    sku: data.sku || `SKU-${data.id}`,
    price: Number(data.price) || 0,
    original_price: data.original_price ? Number(data.original_price) : undefined,
    cost_price: data.cost_price ? Number(data.cost_price) : undefined,
    stock: data.stock ?? data.stock_quantity ?? 0,
    low_stock_threshold: data.low_stock_threshold ?? 10,
    is_active: data.is_active ?? true,
    is_featured: data.is_featured ?? false,
    category_id: data.category_id,
    category: data.category ? transformCategory(data.category) : undefined,
    brand: data.brand,
    weight: data.weight,
    dimensions: data.dimensions,
    primary_image: data.primary_image || data.image_url,
    thumbnail: data.thumbnail || data.primary_image,
    images: (data.images || []).map(transformImage),
    variations: (data.variations || []).map(transformVariation),
    rating_average: data.rating_average ?? data.rating ?? 0,
    rating_count: data.rating_count ?? data.review_count ?? 0,
    sales_count: data.sales_count ?? 0,
    created_at: data.created_at || new Date().toISOString(),
    updated_at: data.updated_at || new Date().toISOString(),
  };
}

function transformCategory(data: any): Category {
  return {
    id: data.id,
    name: data.name,
    slug: data.slug || `category-${data.id}`,
    description: data.description,
    image_url: data.image_url,
    parent_id: data.parent_id,
    product_count: data.product_count,
  };
}

function transformImage(data: any): import('../types/product').ProductImage {
  return {
    id: data.id,
    url: data.url || data.image_url,
    alt_text: data.alt_text || data.alt,
    is_primary: data.is_primary ?? false,
    sort_order: data.sort_order ?? 0,
  };
}

function transformVariation(data: any): import('../types/product').ProductVariation {
  return {
    id: data.id,
    name: data.name,
    value: data.value,
    sku: data.sku,
    price_modifier: data.price_modifier,
    stock: data.stock ?? 0,
    is_active: data.is_active ?? true,
  };
}

function transformReview(data: any): ProductReview {
  return {
    id: data.id,
    user_id: data.user_id,
    user_name: data.user_name || data.user?.full_name || 'Anonymous',
    rating: data.rating,
    title: data.title,
    comment: data.comment || data.content,
    created_at: data.created_at,
    verified_purchase: data.verified_purchase ?? false,
  };
}

// =============================================================================
// SORT HELPERS
// =============================================================================

function mapSortToApi(sort: string): string {
  const sortMap: Record<string, string> = {
    newest: 'created_at',
    oldest: 'created_at',
    price_low: 'price',
    price_high: 'price',
    name_asc: 'name',
    name_desc: 'name',
    rating: 'rating_average',
    popular: 'sales_count',
  };
  return sortMap[sort] || 'created_at';
}

function getSortOrder(sort: string): 'asc' | 'desc' {
  const ascSorts = ['price_low', 'name_asc', 'oldest'];
  return ascSorts.includes(sort) ? 'asc' : 'desc';
}

export default productService;
