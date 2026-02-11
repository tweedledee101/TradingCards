"""
FastAPI Application - Trading Card Platform
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.routes import trending, cards, health, inventory, watchlist

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

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(trending.router, prefix="/api", tags=["Trending"])
app.include_router(cards.router, prefix="/api", tags=["Cards"])
app.include_router(inventory.router, prefix="/api", tags=["Inventory"])
app.include_router(watchlist.router, prefix="/api", tags=["Watchlist"])
