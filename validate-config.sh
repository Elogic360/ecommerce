#!/bin/bash

# Configuration Validation Script
# Ensures no hardcoded URLs exist in the frontend source code

echo "🔍 Scanning for hardcoded URLs in frontend source code..."
echo "=================================================="

FOUND_ISSUES=0

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Change to frontend src directory
cd "$(dirname "$0")/frontend/src" || exit 1

echo ""
echo "Checking TypeScript/JavaScript files..."
echo ""

# Search patterns for common hardcoded values
PATTERNS=(
  "localhost:8000"
  "localhost:3000"
  "127.0.0.1:8000"
  "neatify-o1s6.onrender.com"
  "neatify.netlify.app"
  "915255756642"
)

# Files to exclude from search
EXCLUDE_PATTERNS=(
  "*/node_modules/*"
  "*/.env*"
  "*/README.md"
  "*/CONFIGURATION*.md"
  "*/config/env.ts"  # This file is allowed to have env access
)

# Build exclusion arguments
FIND_EXCLUDE=""
for pattern in "${EXCLUDE_PATTERNS[@]}"; do
  FIND_EXCLUDE="$FIND_EXCLUDE ! -path '$pattern'"
done

# Search for each pattern
for pattern in "${PATTERNS[@]}"; do
  echo "Checking for: $pattern"
  
  # Find files containing the pattern
  RESULTS=$(eval "find . -type f \( -name '*.ts' -o -name '*.tsx' -o -name '*.js' -o -name '*.jsx' \) $FIND_EXCLUDE -exec grep -l '$pattern' {} \;")
  
  if [ -n "$RESULTS" ]; then
    echo -e "${RED}❌ Found hardcoded value '$pattern' in:${NC}"
    echo "$RESULTS" | while read -r file; do
      echo "   $file"
      FOUND_ISSUES=$((FOUND_ISSUES + 1))
    done
    echo ""
  else
    echo -e "${GREEN}✅ No hardcoded '$pattern' found${NC}"
  fi
done

echo ""
echo "=================================================="

# Check for import.meta.env usage outside of config/env.ts
echo ""
echo "Checking for direct import.meta.env usage..."
DIRECT_ENV_USAGE=$(find . -type f \( -name "*.ts" -o -name "*.tsx" \) ! -path "*/config/env.ts" ! -path "*/node_modules/*" -exec grep -l "import\.meta\.env\.VITE_" {} \;)

if [ -n "$DIRECT_ENV_USAGE" ]; then
  echo -e "${YELLOW}⚠️  Found direct environment variable access (should use config):${NC}"
  echo "$DIRECT_ENV_USAGE"
  FOUND_ISSUES=$((FOUND_ISSUES + 1))
else
  echo -e "${GREEN}✅ No direct import.meta.env usage found${NC}"
fi

echo ""
echo "=================================================="

# Final summary
if [ $FOUND_ISSUES -eq 0 ]; then
  echo -e "${GREEN}✅ SUCCESS: No hardcoded URLs or configuration issues found!${NC}"
  echo ""
  echo "Your codebase follows professional configuration best practices:"
  echo "  • All URLs are from environment variables"
  echo "  • Configuration is centralized in src/config/env.ts"
  echo "  • No secrets or production URLs in source code"
  exit 0
else
  echo -e "${RED}❌ FAILED: Found $FOUND_ISSUES configuration issue(s)${NC}"
  echo ""
  echo "Please fix the above issues by:"
  echo "  1. Moving hardcoded values to .env file"
  echo "  2. Accessing them through src/config/env.ts"
  echo "  3. Removing direct import.meta.env usage in service files"
  echo ""
  echo "See frontend/src/config/README.md for guidelines"
  exit 1
fi
