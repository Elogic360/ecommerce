# 🚀 Production Deployment Checklist

**Project:** Neatify E-Commerce Platform  
**Date:** 2026-01-24  
**Status:** Ready for production deployment

---

## PRE-DEPLOYMENT CHECKLIST

### ✅ Phase 1: Configuration Audit (COMPLETE)

- [x] All hardcoded URLs removed from source code
- [x] All secrets in environment variables (not in code)
- [x] Frontend configuration centralized (`src/config/env.ts`)
- [x] Backend configuration enhanced (`app/core/config.py`)
- [x] Production validation implemented
- [x] `.env.example` files complete and documented

### ✅ Phase 2: Dependencies (COMPLETE)

- [x] `requirements.txt` complete with all production dependencies
- [x] `requirements-dev.txt` created for development tools
- [x] All implicit dependencies included (email-validator, etc.)
- [x] Version constraints prevent breaking changes
- [x] Frontend `package.json` verified

### ✅ Phase 3: Security (COMPLETE)

- [x] No secrets committed to version control
- [x] Password hashing uses bcrypt
- [x] JWT tokens properly configured
- [x] CORS origins configurable via environment
- [x] Production validation fails fast if insecure
- [x] Input validation with Pydantic
- [x] SQL injection protection (SQLAlchemy ORM)

---

## DEPLOYMENT STEPS

### 1. Backend Deployment (Render.com)

#### A. Environment Variables
Set the following in Render Dashboard → Environment:

```bash
# CRITICAL - Must Be Set
DATABASE_URL=<your-render-postgres-internal-url>
SECRET_KEY=<generate-with: openssl rand -hex 32>
SESSION_SECRET=<generate-with: openssl rand -hex 32>
ALLOWED_ORIGINS=https://neatify.netlify.app
ENVIRONMENT=production
DEBUG=False

# Application
APP_NAME=Neatify E-Commerce
APP_VERSION=1.5.0

# CORS
CORS_ALLOW_CREDENTIALS=True

# Authentication
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Google OAuth (if using)
GOOGLE_CLIENT_ID=915255756642-sssn2m9k8hrp73f0devrpt39od2c03gv.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=<your-google-client-secret>

# Redis (if using caching)
# REDIS_URL=<your-redis-url>
# CACHE_TTL=300

# Frontend URL (for emails, redirects)
FRONTEND_URL=https://neatify.netlify.app
```

#### B. Build Command
```bash
pip install -r requirements.txt && alembic upgrade head
```

#### C. Start Command
```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

#### D. Health Check
```
Path: /health
Expected Response: {"status": "healthy"}
```

---

### 2. Frontend Deployment (Netlify)

#### A. Environment Variables
Set in Netlify Dashboard → Site settings → Environment variables:

```bash
# API Configuration (REQUIRED)
VITE_API_URL=https://neatify-o1s6.onrender.com/api/v1
VITE_WS_URL=wss://neatify-o1s6.onrender.com
VITE_IMAGE_BASE_URL=https://neatify-o1s6.onrender.com

# Application
VITE_APP_NAME=Neatify
VITE_APP_DESCRIPTION=Your one-stop shop for all household and compound cleaning materials
VITE_APP_VERSION=1.5.0

# Features
VITE_ENABLE_CART_PERSISTENCE=true
VITE_ENABLE_WISHLIST=true
VITE_ENABLE_REVIEWS=true

# Localization
VITE_DEFAULT_CURRENCY=TZS
VITE_DEFAULT_LANGUAGE=en

# Google OAuth (REQUIRED - if using Google Sign-In)
VITE_GOOGLE_CLIENT_ID=915255756642-sssn2m9k8hrp73f0devrpt39od2c03gv.apps.googleusercontent.com

# Third-party (Optional)
# VITE_STRIPE_PUBLISHABLE_KEY=pk_live_...
# VITE_PAYPAL_CLIENT_ID=...
# VITE_GA_TRACKING_ID=UA-...

# Contact
VITE_CONTACT_EMAIL=support@neatify.market
VITE_CONTACT_PHONE=+255...

# Social Media
VITE_FACEBOOK_URL=https://facebook.com/neatify
VITE_TWITTER_URL=https://twitter.com/neatify
VITE_INSTAGRAM_URL=https://instagram.com/neatify
```

#### B. Build Command
```bash
npm run build
# or: pnpm build
```

#### C. Publish Directory
```
dist
```

#### D. Build Settings (netlify.toml)
Already configured in `netlify.toml`:
- Redirects for SPA routing
- Security headers
- Asset optimization

---

### 3. Database Setup

#### A. Run Migrations
```bash
# On Render, this runs automatically in build command
alembic upgrade head
```

#### B. Verify Database
```bash
# Check admin account exists
python verify_admin.py
```

#### C. Seed Data (Optional)
```bash
# Only if you want demo data
python seed.py
```

---

### 4. Post-Deployment Verification

#### Backend Health Checks
```bash
# Health endpoint
curl https://neatify-o1s6.onrender.com/health
# Expected: {"status":"healthy"}

# API docs
curl https://neatify-o1s6.onrender.com/docs
# Expected: OpenAPI documentation page

# Test login
curl -X POST https://neatify-o1s6.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@neatify.market&password=<your-password>"
# Expected: {"access_token":"...","token_type":"bearer"}
```

#### Frontend Health Checks
```bash
# Verify site loads
curl https://neatify.netlify.app/
# Expected: HTML content

# Verify API connectivity (from browser console)
fetch('https://neatify-o1s6.onrender.com/api/v1/products?limit=1')
  .then(r => r.json())
  .then(console.log)
# Expected: Product list data
```

#### CORS Verification
```bash
# From browser console on https://neatify.netlify.app
fetch('https://neatify-o1s6.onrender.com/api/v1/products')
  .then(r => console.log('CORS OK'))
  .catch(e => console.error('CORS Error:', e))
# Expected: "CORS OK"
```

---

## CRITICAL SECURITY CHECKS

### Before Going Live

- [ ] **SECRET_KEY**: Generated with `openssl rand -hex 32`, not default
- [ ] **SESSION_SECRET**: Generated separately, not default
- [ ] **ADMIN_PASSWORD**: Changed from default "admin123"
- [ ] **DEBUG**: Set to `False` in production
- [ ] **ALLOWED_ORIGINS**: Set to actual frontend URL only
- [ ] **DATABASE_URL**: Using production database, not localhost
- [ ] **HTTPS**: Both frontend and backend use HTTPS only
- [ ] **.env files**: Not committed to git (check .gitignore)

### Run Security Validation
```bash
# Backend security check (automatic on startup)
# Will exit(1) if insecure configuration detected

# Manual verification
cd backend
python -c "from app.core.config import settings; settings.validate_production_config()"
# Expected: No output if secure, error if insecure
```

---

##  ROLLBACK PLAN

### If Deployment Fails

#### Backend Issues
1. Check Render logs for errors
2. Verify all environment variables are set
3. Check database connection
4. Roll back to previous deployment in Render dashboard

#### Frontend Issues
1. Check Netlify deploy logs
2. Verify environment variables are set
3. Check API connectivity from built site
4. Roll back to previous deploy in Netlify dashboard

### Emergency Contacts
- **Backend Logs**: Render Dashboard → Logs
- **Frontend Logs**: Netlify Dashboard → Deploys → Deploy log
- **Database**: Render Dashboard → PostgreSQL → Logs

---

## POST-DEPLOYMENT MONITORING

### Week 1 Checklist
- [ ] Monitor error rates (target: <1%)
- [ ] Check response times (target: <500ms for API)
- [ ] Verify all features working
- [ ] Check database performance
- [ ] Monitor cache hit rates (if using Redis)
- [ ] Review user feedback
- [ ] Check for security alerts

### Ongoing Monitoring
- **Daily**: Check error logs
- **Weekly**: Review performance metrics
- **Monthly**: Security audit & dependency updates
- **Quarterly**: Full code review

---

## 📊 SUCCESS CRITERIA

### Deployment is successful if:
- ✅ All health endpoints return 200 OK
- ✅ Frontend loads without errors
- ✅ Users can login successfully
- ✅ Products display correctly
- ✅ Images load properly
- ✅ Cart functionality works
- ✅ Orders can be placed
- ✅ Admin panel accessible
- ✅ No CORS errors
- ✅ No console errors in browser

---

## 🎉 CONGRATULATIONS!

If all checks pass, your application is successfully deployed to production!

**Next Steps:**
1. Monitor for first 24-48 hours
2. Collect user feedback
3. Plan for continuous improvement
4. Keep dependencies up to date
5. Regular security audits

---

**Deployment Date:** _________________  
**Deployed By:** _________________  
**Verified By:** _________________  
**Status:** _________________  

---

**For support or issues, refer to:**
- `EXECUTIVE_SUMMARY.md` - Complete audit results
- `CONFIGURATION_AUDIT_REPORT.md` - Configuration details
- `QUICK_CONFIG_REFERENCE.md` - Quick reference
- `frontend/src/config/README.md` - Frontend configuration guide
