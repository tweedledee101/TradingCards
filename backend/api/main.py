"""
FastAPI Application - Trading Card Platform
"""
import time
import uuid
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from backend.api.routes import trending, cards, health, inventory, watchlist, webhooks, ebay_compliance, opportunities, sourcing, scheduled_bids
from backend.utils.logger import get_logger, set_request_id, clear_request_id

log = get_logger('api')

app = FastAPI(
    title="Trading Card Platform API",
    description="API for detecting trending trading cards and managing inventory",
    version="0.3.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log every request with timing. Catch unhandled errors."""
    request_id = str(uuid.uuid4())[:8]
    set_request_id(request_id)
    start = time.time()

    try:
        response = await call_next(request)
        duration_ms = round((time.time() - start) * 1000)

        # Log slow requests as warnings
        if duration_ms > 5000:
            log.warn('Slow request', category='slow_request', context={
                'method': request.method,
                'path': str(request.url.path),
                'duration_ms': duration_ms,
                'status': response.status_code
            })

        response.headers['X-Request-ID'] = request_id
        return response

    except Exception as exc:
        duration_ms = round((time.time() - start) * 1000)
        log.error(f'Unhandled error: {exc}', category='unhandled_error', context={
            'method': request.method,
            'path': str(request.url.path),
            'duration_ms': duration_ms
        })
        return JSONResponse(status_code=500, content={
            'detail': 'Internal server error',
            'request_id': request_id
        })
    finally:
        clear_request_id()

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(opportunities.router, prefix="/api", tags=["Opportunities"])
app.include_router(trending.router, prefix="/api", tags=["Trending"])
app.include_router(cards.router, prefix="/api", tags=["Cards"])
app.include_router(inventory.router, prefix="/api", tags=["Inventory"])
app.include_router(watchlist.router, prefix="/api", tags=["Watchlist"])
app.include_router(webhooks.router, prefix="/api", tags=["Webhooks"])
app.include_router(ebay_compliance.router, prefix="/api", tags=["eBay Compliance"])
app.include_router(sourcing.router, prefix="/api", tags=["Sourcing"])
app.include_router(scheduled_bids.router, prefix="/api", tags=["Scheduled Bids"])
