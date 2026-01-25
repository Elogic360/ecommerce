# 🚀 Quick Configuration Reference

## Essential Commands

### Development
```bash
# 1. Copy environment template
cp frontend/.env.example frontend/.env

# 2. Edit with your local values
# Change VITE_API_URL to http://localhost:8000/api/v1

# 3. Start dev server
cd frontend && npm run dev
```

### Production (Netlify)
```bash
# Set in Netlify Dashboard → Site Settings → Environment Variables
VITE_API_URL=https://neatify-o1s6.onrender.com/api/v1
VITE_WS_URL=wss://neatify-o1s6.onrender.com
VITE_GOOGLE_CLIENT_ID=915255756642-sssn2m9k8hrp73f0devrpt39od2c03gv.apps.googleusercontent.com
VITE_IMAGE_BASE_URL=https://neatify-o1s6.onrender.com
```

## Common Tasks

### Access API Configuration
```typescript
import { config } from '@/config/env';

// Get API URL
const apiUrl = config.api.url;

// Create axios instance
const api = axios.create({
  baseURL: config.api.url,
});
```

### Get Image URLs
```typescript
import { getImageUrl } from '@/config/env';

const imageUrl = getImageUrl(product.image_path);
// Automatically handles absolute URLs, relative paths, and null values
```

### Check Feature Flags
```typescript
import { config } from '@/config/env';

if (config.features.enableWishlist) {
  // Show wishlist UI
}
```

### WebSocket Connection
```typescript
import { config } from '@/config/env';

// Automatically uses VITE_WS_URL
// Already implemented in src/hooks/useWebSocket.ts
```

## Validation

### Run Configuration Validation
```bash
# Check for hardcoded URLs
./validate-config.sh
```

### Manual Check
```bash
cd frontend/src
grep -r "localhost:8000" . --include="*.ts" --include="*.tsx"
# Should return nothing!
```

## Troubleshooting

### Issue: "Missing required environment variables"
**Solution:** Set `VITE_API_URL` in your environment
```bash
# Development (.env file)
VITE_API_URL=http://localhost:8000/api/v1

# Production (Netlify Dashboard)
VITE_API_URL=https://your-backend.onrender.com/api/v1
```

### Issue: Configuration not updating
**Solution:** Restart dev server after changing .env
```bash
# Kill dev server (Ctrl+C)
npm run dev  # Start again
```

### Issue: Google Sign-In not working
**Solution:** Set VITE_GOOGLE_CLIENT_ID
```bash
VITE_GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
```

## File Locations

- **Configuration Module:** `frontend/src/config/env.ts`
- **Environment Template:** `frontend/.env.example`
- **Your Environment:** `frontend/.env` (gitignored)
- **Documentation:** `frontend/src/config/README.md`
- **Summary:** `frontend/CONFIGURATION_REFACTORING.md`

## Rules

### ✅ DO
- Import from `@/config/env`
- Set values in `.env` files
- Document new variables in `.env.example`

### ❌ DON'T
- Hardcode URLs in code
- Use `import.meta.env.VITE_*` in service files
- Commit `.env` to git
- Use fallback values for production URLs

## Migration Example

### Before ❌
```typescript
const API_URL = import.meta.env.VITE_API_URL || 'https://hardcoded.com/api/v1';
```

### After ✅
```typescript
import { config } from '@/config/env';
// Use config.api.url everywhere
```

---

**Quick Links:**
- [Full Documentation](./frontend/src/config/README.md)
- [Detailed Summary](./frontend/CONFIGURATION_REFACTORING.md)
- [Environment Variables](./frontend/.env.example)
