"""
FastAPI Application - Trading Card Platform
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.routes import trending, cards, health

app = FastAPI(
    title="Trading Card Platform API",
    description="API for detecting trending trading cards",
    version="0.2.0"
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
