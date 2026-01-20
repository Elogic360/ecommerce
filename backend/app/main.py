from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.core.rate_limit import RateLimitMiddleware
from app.routers import (
    auth, products, cart, admin, orders, inventory, categories,
    wishlist, coupons, loyalty, notifications, analytics, returns, shipping,
    websockets, dashboard
)
from app.db.base import Base
from app.db.session import engine
import os
import logging
import traceback

# Create database tables
# Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="ShopHub E-Commerce API with Admin Dashboard"
)

# Exception logging middleware to capture unexpected errors and stack traces
logger = logging.getLogger("shophub")

@app.middleware("http")
async def log_exceptions(request, call_next):
    try:
        response = await call_next(request)
        return response
    except Exception as exc:  # capture unexpected exceptions
        # Log full stack trace for easier debugging
        logger.exception("Unhandled exception during request: %s %s", request.method, request.url)
        # Re-raise so FastAPI / Uvicorn can handle response and return 500
        raise

# Rate limiting middleware (should be added first)
if settings.RATE_LIMIT_ENABLED:
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=settings.RATE_LIMIT_PER_MINUTE
    )

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(',') if settings.ALLOWED_ORIGINS else ["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create uploads directory
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

# Mount static files
upload_base_dir = os.path.dirname(settings.UPLOAD_DIR)
if os.path.exists(upload_base_dir):
    app.mount("/uploads", StaticFiles(directory=upload_base_dir), name="uploads")

# Include routers
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["Authentication"])
app.include_router(products.router, prefix=f"{settings.API_V1_STR}", tags=["Products"])
app.include_router(categories.router, prefix=f"{settings.API_V1_STR}", tags=["Categories"])
app.include_router(cart.router, prefix=f"{settings.API_V1_STR}", tags=["Cart"])
app.include_router(admin.router, prefix=f"{settings.API_V1_STR}/admin", tags=["Admin"])
app.include_router(dashboard.router, prefix=f"{settings.API_V1_STR}/admin/dashboard", tags=["Dashboard"])
app.include_router(orders.router, prefix=f"{settings.API_V1_STR}", tags=["Orders"])
app.include_router(inventory.router, prefix=f"{settings.API_V1_STR}/admin", tags=["Inventory"])

# V1.5 Feature Routers
app.include_router(wishlist.router, prefix=f"{settings.API_V1_STR}/wishlist", tags=["Wishlist"])
app.include_router(coupons.router, prefix=f"{settings.API_V1_STR}/coupons", tags=["Coupons"])
app.include_router(loyalty.router, prefix=f"{settings.API_V1_STR}/loyalty", tags=["Loyalty"])
app.include_router(notifications.router, prefix=f"{settings.API_V1_STR}/notifications", tags=["Notifications"])
app.include_router(analytics.router, prefix=f"{settings.API_V1_STR}/admin/analytics", tags=["Analytics"])
app.include_router(returns.router, prefix=f"{settings.API_V1_STR}/returns", tags=["Returns"])
app.include_router(shipping.router, prefix=f"{settings.API_V1_STR}/admin/shipping", tags=["Shipping"])

# WebSocket Router
app.include_router(websockets.router, tags=["WebSocket"])

@app.get("/")
def read_root():
    return {"message": "Welcome to ShopHub E-Commerce API"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/api/v1")
def api_info():
    return {
        "message": "ShopHub E-Commerce API v1",
        "docs": "/docs",
        "redoc": "/redoc"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
