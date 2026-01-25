/**
 * Environment Configuration
 * Centralized configuration management for environment variables.
 * All environment-specific values should be accessed through this file.
 * 
 * SECURITY NOTE: Never hardcode production URLs, API keys, or secrets in code.
 * All values should come from environment variables with safe defaults for development only.
 */

/**
 * Validates that required environment variables are present.
 * Throws an error in production if critical variables are missing.
 */
const validateEnv = () => {
    const isProduction = import.meta.env.PROD;
    const requiredVars = ['VITE_API_URL'];

    if (isProduction) {
        const missing = requiredVars.filter(
            (varName) => !import.meta.env[varName]
        );

        if (missing.length > 0) {
            throw new Error(
                `Missing required environment variables: ${missing.join(', ')}\n` +
                'Please configure these in your deployment environment.'
            );
        }
    }
};

// Validate on module load
validateEnv();

/**
 * Application Environment Configuration
 */
export const config = {
    /**
     * API Configuration
     */
    api: {
        /** Backend API base URL with /api/v1 suffix */
        url: import.meta.env.VITE_API_URL as string,

        /** Backend base URL without /api/v1 suffix */
        baseUrl: import.meta.env.VITE_API_URL
            ? (import.meta.env.VITE_API_URL as string).replace('/api/v1', '')
            : undefined,
    },

    /**
     * WebSocket Configuration
     */
    websocket: {
        /** WebSocket server URL */
        url: import.meta.env.VITE_WS_URL as string | undefined,
    },

    /**
     * Application Metadata
     */
    app: {
        name: import.meta.env.VITE_APP_NAME || 'Neatify',
        description: import.meta.env.VITE_APP_DESCRIPTION || 'E-Commerce Platform',
        version: import.meta.env.VITE_APP_VERSION || '1.0.0',
        environment: import.meta.env.MODE,
    },

    /**
     * Feature Flags
     */
    features: {
        enableCartPersistence: import.meta.env.VITE_ENABLE_CART_PERSISTENCE === 'true',
        enableWishlist: import.meta.env.VITE_ENABLE_WISHLIST === 'true',
        enableReviews: import.meta.env.VITE_ENABLE_REVIEWS === 'true',
    },

    /**
     * Third-Party Services
     */
    services: {
        google: {
            clientId: import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined,
        },
        stripe: {
            publishableKey: import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY as string | undefined,
        },
        paypal: {
            clientId: import.meta.env.VITE_PAYPAL_CLIENT_ID as string | undefined,
        },
        analytics: {
            gaTrackingId: import.meta.env.VITE_GA_TRACKING_ID as string | undefined,
        },
    },

    /**
     * Localization
     */
    locale: {
        defaultCurrency: import.meta.env.VITE_DEFAULT_CURRENCY || 'TZS',
        defaultLanguage: import.meta.env.VITE_DEFAULT_LANGUAGE || 'en',
    },

    /**
     * Assets Configuration
     */
    assets: {
        imageBaseUrl: import.meta.env.VITE_IMAGE_BASE_URL as string | undefined,
        cdnUrl: import.meta.env.VITE_CDN_URL as string | undefined,
        defaultProductImage: import.meta.env.VITE_DEFAULT_PRODUCT_IMAGE || '/placeholder-product.svg',
    },

    /**
     * Social Media Links
     */
    social: {
        facebook: import.meta.env.VITE_FACEBOOK_URL as string | undefined,
        twitter: import.meta.env.VITE_TWITTER_URL as string | undefined,
        instagram: import.meta.env.VITE_INSTAGRAM_URL as string | undefined,
    },

    /**
     * Contact Information
     */
    contact: {
        email: import.meta.env.VITE_CONTACT_EMAIL as string | undefined,
        phone: import.meta.env.VITE_CONTACT_PHONE as string | undefined,
    },

    /**
     * Pagination Settings
     */
    pagination: {
        defaultPageSize: Number(import.meta.env.VITE_DEFAULT_PAGE_SIZE) || 12,
        maxPageSize: Number(import.meta.env.VITE_MAX_PAGE_SIZE) || 48,
    },

    /**
     * Development flags
     */
    dev: {
        isDevelopment: import.meta.env.DEV,
        isProduction: import.meta.env.PROD,
    },
} as const;

/**
 * Type-safe environment configuration
 */
export type AppConfig = typeof config;

/**
 * Helper function to get full image URL
 * @param imagePath - Relative or absolute image path
 * @returns Full URL to the image
 */
export const getImageUrl = (imagePath: string | null | undefined): string => {
    if (!imagePath) return config.assets.defaultProductImage;
    if (imagePath.startsWith('http')) return imagePath;

    const baseUrl = config.assets.imageBaseUrl || config.api.baseUrl;
    if (!baseUrl) {
        console.warn('No image base URL configured, using relative path');
        return imagePath;
    }

    const normalized = imagePath.startsWith('/') ? imagePath : `/${imagePath}`;
    return `${baseUrl}${normalized}`;
};

/**
 * Export individual helpers for convenience
 */
export const isProduction = config.dev.isProduction;
export const isDevelopment = config.dev.isDevelopment;

export default config;
