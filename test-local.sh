#!/bin/bash

echo "🧪 Testing Local Deployment Configuration"
echo "=========================================="

# Test backend configuration
echo ""
echo "📦 Backend Configuration:"
cd /home/elogic360/Documents/CODELAB/e_commerce&store01/backend
if grep -q "ALLOWED_ORIGINS=" .env; then
    echo "✅ ALLOWED_ORIGINS is set"
    grep "ALLOWED_ORIGINS=" .env
else
    echo "❌ ALLOWED_ORIGINS not found in .env"
fi

# Test frontend configuration
echo ""
echo "🎨 Frontend Configuration:"
cd /home/elogic360/Documents/CODELAB/e_commerce&store01/frontend
if grep -q "VITE_API_URL=" .env; then
    echo "✅ VITE_API_URL is set"
    grep "VITE_API_URL=" .env
else
    echo "❌ VITE_API_URL not found in .env"
fi

echo ""
echo "=========================================="
echo "✅ Configuration check complete!"
echo ""
echo "Next steps:"
echo "1. Start backend: cd backend && source venv/bin/activate && uvicorn app.main:app --reload"
echo "2. Start frontend: cd frontend && npm run dev"
echo "3. Open browser: http://localhost:5173"
