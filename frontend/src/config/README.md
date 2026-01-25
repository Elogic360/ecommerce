# Frontend Environment Configuration

## Overview

This directory contains the centralized environment configuration system for the Neatify e-commerce frontend.

## File Structure

- **`env.ts`** - Centralized configuration module that:
  - Validates required environment variables
  - Provides type-safe access to all configuration
  - Includes helper functions for common tasks
  - Prevents hardcoded values in the codebase

## Important Security Rules

### ✅ DO
- **Always** access configuration through `import { config } from '@/config/env'`
- Set all environment-specific values in `.env` files
- Use `import.meta.env.VITE_*` only in the `env.ts` file
- Validate required variables in production
- Document all environment variables in `.env.example`

### ❌ DON'T
- **Never** hardcode URLs, API keys, or secrets in code
- **Never** use fallback values for production URLs in code
- **Never** commit `.env` files to version control
- **Never** access `import.meta.env` directly in service files

## Usage Examples

### Accessing API Configuration

```typescript
import { config } from '@/config/env';
import axios from 'axios';

// ✅ CORRECT - Use centralized config
const api = axios.create({
  baseURL: config.api.url,
});

// ❌ WRONG - Never hardcode URLs
const api = axios.create({
  baseURL: 'https://api.example.com/api/v1',
});

// ❌ WRONG - Never access env vars directly in services
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'https://fallback.com/api/v1',
});
```

### Using Helper Functions

```typescript
import { getImageUrl, config } from '@/config/env';

// ✅ CORRECT - Use provided helper
const imageUrl = getImageUrl(product.image_path);

// Check feature flags
if (config.features.enableWishlist) {
  // Show wishlist feature
}

// Access third-party service configuration
const googleClientId = config.services.google.clientId;
```

### Validation

The configuration system automatically validates required variables in production:

```typescript
// This will throw an error in production if VITE_API_URL is not set
import { config } from '@/config/env';
```

## Environment Variables

See `../.env.example` for a complete list of available environment variables.

### Required Variables (Production)
- `VITE_API_URL` - Backend API URL with `/api/v1` suffix

### Recommended Variables
- `VITE_WS_URL` - WebSocket URL for real-time features
- `VITE_GOOGLE_CLIENT_ID` - For Google OAuth sign-in
- `VITE_IMAGE_BASE_URL` - Base URL for product images

## Setup Instructions

### Development

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Update `.env` with your local values:
   ```env
   VITE_API_URL=http://localhost:8000/api/v1
   VITE_WS_URL=ws://localhost:8000
   ```

### Production (Netlify/Vercel)

Set environment variables in your deployment platform:

**Netlify:**
1. Go to Site Settings → Environment Variables
2. Add all required variables:
   - `VITE_API_URL=https://your-backend.onrender.com/api/v1`
   - `VITE_WS_URL=wss://your-backend.onrender.com`
   - etc.

**Vercel:**
1. Go to Project Settings → Environment Variables
2. Add the same variables as above

## Migration Guide

If you're migrating from hardcoded URLs:

### Before (❌ Bad Practice)
```typescript
const API_URL = import.meta.env.VITE_API_URL || 'https://hardcoded-url.com/api/v1';
```

### After (✅ Good Practice)
```typescript
import { config } from '@/config/env';
// Use config.api.url throughout your code
```

## TypeScript Support

The configuration is fully typed:

```typescript
import { config, type AppConfig } from '@/config/env';

// All properties are type-checked
const apiUrl: string = config.api.url;
const isProduction: boolean = config.dev.isProduction;
```

## Troubleshooting

### "Missing required environment variables" Error

**Problem:** You see this error when building or running in production.

**Solution:** 
1. Ensure `VITE_API_URL` is set in your deployment environment
2. Check that the variable name is correct (case-sensitive)
3. Verify the value includes the `/api/v1` suffix

### Configuration Not Updating

**Problem:** Changes to `.env` don't reflect in the app.

**Solution:**
1. Restart the dev server after changing `.env`
2. Clear browser cache
3. Verify you're editing the correct `.env` file (not `.env.example`)

## Best Practices

1. **Single Source of Truth**: All configuration in one place (`env.ts`)
2. **Type Safety**: Use TypeScript types for configuration
3. **Validation**: Validate required variables at startup
4. **Documentation**: Keep `.env.example` up to date
5. **Security**: Never commit secrets or production URLs to code
6. **Flexibility**: Support multiple environments (dev, staging, prod)

## Contributing

When adding new environment variables:

1. Add to `env.ts` with proper typing
2. Document in `.env.example` with description
3. Update this README if it's a major change
4. Update deployment documentation
