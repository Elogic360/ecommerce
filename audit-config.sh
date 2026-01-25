#!/bin/bash

# Complete Project Configuration Audit
# Scans both frontend and backend for hardcoded URLs and insecure configurations

echo "🔍 COMPLETE PROJECT CONFIGURATION AUDIT"
echo "========================================"
echo ""

FOUND_ISSUES=0

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# FRONTEND AUDIT
# ============================================================================

echo -e "${BLUE}━━━ FRONTEND AUDIT ━━━${NC}"
echo ""

cd "$(dirname "$0")/frontend/src" || exit 1

# Patterns to search for
FRONTEND_PATTERNS=(
  "localhost:8000"
  "localhost:3000"
  "127.0.0.1:8000"
  "neatify-o1s6.onrender.com"
  "neatify.netlify.app"
  "915255756642"  # Google Client ID
)

# Check for hardcoded values in frontend
for pattern in "${FRONTEND_PATTERNS[@]}"; do
  echo "Checking for: $pattern"
  
  RESULTS=$(find . -type f \( -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" \) \
    ! -path "*/node_modules/*" \
    ! -path "*/config/env.ts" \
    -exec grep -l "$pattern" {} \;)
  
  if [ -n "$RESULTS" ]; then
    echo -e "${RED}❌ Found hardcoded '$pattern' in frontend:${NC}"
    echo "$RESULTS"
    FOUND_ISSUES=$((FOUND_ISSUES + 1))
  else
    echo -e "${GREEN}✅ Clean${NC}"
  fi
done

# Check for direct import.meta.env usage (should use config)
echo ""
echo "Checking for direct import.meta.env usage..."
DIRECT_ENV=$(find . -type f \( -name "*.ts" -o -name "*.tsx" \) \
  ! -path "*/config/env.ts" \
  ! -path "*/node_modules/*" \
  -exec grep -l "import\.meta\.env\.VITE_" {} \;)

if [ -n "$DIRECT_ENV" ]; then
  echo -e "${YELLOW}⚠️  Found direct env access (should use @/config/env):${NC}"
  echo "$DIRECT_ENV"
  FOUND_ISSUES=$((FOUND_ISSUES + 1))
else
  echo -e "${GREEN}✅ All using centralized config${NC}"
fi

echo ""

# ============================================================================
# BACKEND AUDIT
# ============================================================================

cd "$(dirname "$0")/backend" || exit 1

echo -e "${BLUE}━━━ BACKEND AUDIT ━━━${NC}"
echo ""

# Check for hardcoded secrets/passwords in config
echo "Checking for default secrets in production config..."
DEFAULT_SECRETS=0

# Check if SECRET_KEY default is being used with ENVIRONMENT=production
if grep -q 'SECRET_KEY.*your-secret-key-change-in-production' app/core/config.py; then
  if [ -f ".env" ] && grep -q "ENVIRONMENT=production" .env; then
    if ! grep -q "^SECRET_KEY=" .env || grep -q "^SECRET_KEY=your-secret-key" .env; then
      echo -e "${RED}❌ Using default SECRET_KEY in production${NC}"
      DEFAULT_SECRETS=$((DEFAULT_SECRETS + 1))
    fi
  fi
fi

if [ $DEFAULT_SECRETS -eq 0 ]; then
  echo -e "${GREEN}✅ No default secrets detected${NC}"
else
  FOUND_ISSUES=$((FOUND_ISSUES + DEFAULT_SECRETS))
fi

echo ""

# Check for hardcoded database URLs (not in config.py, which has dev default)
echo "Checking for hardcoded database URLs in application code..."
DB_URLS=$(find app -type f -name "*.py" \
  ! -path "*/config.py" \
  ! -path "*/__pycache__/*" \
  -exec grep -l "postgresql://\|postgres://" {} \;)

if [ -n "$DB_URLS" ]; then
  echo -e "${RED}❌ Found hardcoded database URLs:${NC}"
  echo "$DB_URLS"
  FOUND_ISSUES=$((FOUND_ISSUES + 1))
else
  echo -e "${GREEN}✅ No hardcoded database URLs in app code${NC}"
fi

echo ""

# Check for hardcoded production URLs in backend code
echo "Checking for hardcoded production URLs..."
PROD_URLS=$(find app -type f -name "*.py" \
  ! -path "*/seed.py" \
  ! -path "*/config.py" \
  ! -path "*/__pycache__/*" \
  -exec grep -l "neatify.*\.onrender\.com\|neatify.*\.netlify\.app" {} \;)

if [ -n "$PROD_URLS" ]; then
  echo -e "${RED}❌ Found hardcoded production URLs:${NC}"
  echo "$PROD_URLS"
  FOUND_ISSUES=$((FOUND_ISSUES + 1))
else
  echo -e "${GREEN}✅ No hardcoded production URLs${NC}"
fi

echo ""

# ============================================================================
# ENVIRONMENT FILES AUDIT
# ============================================================================

cd "$(dirname "$0")" || exit 1

echo -e "${BLUE}━━━ ENVIRONMENT FILES AUDIT ━━━${NC}"
echo ""

# Check .env files are not in git
echo "Checking .env files are gitignored..."
if git check-ignore frontend/.env backend/.env > /dev/null 2>&1; then
  echo -e "${GREEN}✅ .env files are properly gitignored${NC}"
else
  echo -e "${RED}❌ .env files might not be gitignored!${NC}"
  FOUND_ISSUES=$((FOUND_ISSUES + 1))
fi

# Check .env.example files exist
echo "Checking .env.example files exist..."
MISSING_EXAMPLES=0

if [ ! -f "frontend/.env.example" ]; then
  echo -e "${RED}❌ Missing frontend/.env.example${NC}"
  MISSING_EXAMPLES=$((MISSING_EXAMPLES + 1))
fi

if [ ! -f "backend/.env.example" ]; then
  echo -e "${RED}❌ Missing backend/.env.example${NC}"
  MISSING_EXAMPLES=$((MISSING_EXAMPLES + 1))
fi

if [ $MISSING_EXAMPLES -eq 0 ]; then
  echo -e "${GREEN}✅ All .env.example files present${NC}"
else
  FOUND_ISSUES=$((FOUND_ISSUES + MISSING_EXAMPLES))
fi

echo ""

# ============================================================================
# DOCUMENTATION AUDIT
# ============================================================================

echo -e "${BLUE}━━━ DOCUMENTATION AUDIT ━━━${NC}"
echo ""

MISSING_DOCS=0

if [ ! -f "frontend/src/config/README.md" ]; then
  echo -e "${YELLOW}⚠️  Missing frontend/src/config/README.md${NC}"
  MISSING_DOCS=$((MISSING_DOCS + 1))
fi

if [ ! -f "frontend/src/config/env.ts" ]; then
  echo -e "${RED}❌ Missing frontend/src/config/env.ts (critical!)${NC}"
  MISSING_DOCS=$((MISSING_DOCS + 1))
  FOUND_ISSUES=$((FOUND_ISSUES + 1))
fi

if [ $MISSING_DOCS -eq 0 ]; then
  echo -e "${GREEN}✅ All documentation present${NC}"
fi

echo ""

# ============================================================================
# FINAL REPORT
# ============================================================================

echo "========================================"
echo ""

if [ $FOUND_ISSUES -eq 0 ]; then
  echo -e "${GREEN}✅ ✅ ✅ AUDIT PASSED ✅ ✅ ✅${NC}"
  echo ""
  echo "✅ No hardcoded URLs found"
  echo "✅ Configuration is centralized"
  echo "✅ Environment files properly managed"
  echo "✅ Documentation is complete"
  echo ""
  echo "Your project follows professional configuration best practices!"
  exit 0
else
  echo -e "${RED}❌ ❌ ❌ AUDIT FAILED ❌ ❌ ❌${NC}"
  echo ""
  echo "Found $FOUND_ISSUES configuration issue(s)"
  echo ""
  echo "Please fix these issues by:"
  echo "  1. Moving hardcoded values to environment variables"
  echo "  2. Using centralized configuration (frontend/src/config/env.ts)"
  echo "  3. Accessing settings through settings object (backend)"
  echo "  4. Ensuring .env files are gitignored"
  echo ""
  echo "See documentation:"
  echo "  - frontend/src/config/README.md"
  echo "  - frontend/CONFIGURATION_REFACTORING.md"
  echo "  - QUICK_CONFIG_REFERENCE.md"
  exit 1
fi
