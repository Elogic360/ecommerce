from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
# from fastapi_cache import FastAPICache
# from fastapi_cache.backends.redis import RedisBackend
# from redis import asyncio as aioredis
from app.core.config import settings
from app.core.rate_limit import RateLimitMiddleware
from app.routers import (
    auth, products, cart, admin, orders, inventory, inventory_public, categories,
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
    description="Neatify E-Commerce API with Admin Dashboard"
)

# Exception logging middleware to capture unexpected errors and stack traces
logger = logging.getLogger("neatify")


class ExceptionHandlingMiddleware(BaseHTTPMiddleware):
    """Top-level middleware to catch unhandled exceptions and return JSON
    responses that include CORS headers so browsers can read error bodies.
    This middleware is registered via `app.add_middleware` before CORSMiddleware
    and rate-limit middleware to ensure it runs outermost.
    """

    async def dispatch(self, request: StarletteRequest, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            # Log full stack trace for easier debugging
            logger.exception("Unhandled exception during request: %s %s", request.method, request.url)

            # Determine allowed origins from settings (same as CORSMiddleware config)
            try:
                allowed = settings.cors_origins_list
            except Exception as config_error:
                # If we cannot access config during an exception, log and use wildcard
                logger.error("Cannot access CORS config during exception handling: %s", config_error)
                allowed = []

            origin = request.headers.get("origin")
            response_headers = {}
            if origin and allowed and origin in allowed:
                response_headers["Access-Control-Allow-Origin"] = origin
            else:
                # Use wildcard only when config is unavailable (exception scenario)
                response_headers["Access-Control-Allow-Origin"] = "*"

            response_headers.update({
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS,PATCH,HEAD",
                "Access-Control-Allow-Headers": "authorization,content-type",
            })

            # Avoid returning internal details in production
            if getattr(settings, "ENV", "production") == "development":
                content = {"detail": str(exc)}
            else:
                content = {"detail": "Internal server error"}

            return JSONResponse(status_code=500, content=content, headers=response_headers)

# Rate limiting middleware (should be added first)
if settings.RATE_LIMIT_ENABLED:
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=settings.RATE_LIMIT_PER_MINUTE
    )

# Register our exception handling middleware BEFORE other middlewares so it
# can catch errors thrown by them and still return CORS headers.
app.add_middleware(ExceptionHandlingMiddleware)

# CORS middleware
# Use centralized configuration helper for parsing origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create uploads directory
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

# Custom StaticFiles to add security headers (fix ORB)
class SecurityStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        # Add CORP header to prevent OpaqueResponseBlocking
        response.headers["Cross-Origin-Resource-Policy"] = "cross-origin"
        # Ensure CORS is also explicitly allowed for these assets
        response.headers["Access-Control-Allow-Origin"] = "*"
        return response

# Mount static files
upload_base_dir = os.path.dirname(settings.UPLOAD_DIR)
if os.path.exists(upload_base_dir):
    app.mount("/uploads", SecurityStaticFiles(directory=upload_base_dir), name="uploads")

# Initialize Redis cache
@app.on_event("startup")
async def startup_event():
    try:
        # redis = aioredis.from_url(settings.REDIS_URL, encoding="utf8", decode_responses=True)
        # FastAPICache.init(RedisBackend(redis), prefix="fasthub-cache")
        logger.info("Cache initialization skipped - Redis not available")
    except Exception as e:
        logger.warning(f"Failed to initialize Redis cache: {e}. Continuing without cache.")

# Include routers
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["Authentication"])
app.include_router(products.router, prefix=f"{settings.API_V1_STR}", tags=["Products"])
app.include_router(categories.router, prefix=f"{settings.API_V1_STR}", tags=["Categories"])
app.include_router(cart.router, prefix=f"{settings.API_V1_STR}", tags=["Cart"])
app.include_router(admin.router, prefix=f"{settings.API_V1_STR}/admin", tags=["Admin"])
app.include_router(dashboard.router, prefix=f"{settings.API_V1_STR}/admin/dashboard", tags=["Dashboard"])
app.include_router(orders.router, prefix=f"{settings.API_V1_STR}", tags=["Orders"])
app.include_router(inventory.router, prefix=f"{settings.API_V1_STR}/admin", tags=["Inventory"])
app.include_router(inventory_public.router, prefix=f"{settings.API_V1_STR}/inventory", tags=["Public Inventory"])

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
    return {"message": "Welcome to Neatify - Cleaning Supplies & Tools API"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/time")
def get_server_time():
    """Get current server time for timezone verification"""
    from datetime import datetime
    return {
        "server_time": datetime.utcnow().isoformat() + "Z",
        "timezone": settings.TIMEZONE
    }

@app.get("/api/v1")
def api_info():
    return {
        "message": "Neatify - Cleaning Supplies & Tools API v1",
        "docs": "/docs",
        "redoc": "/redoc"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
