# app/main.py
"""
FastAPI application for Invoice Intelligence Agent
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.database import init_db
from app.api.routes import invoices_router, chat_router

# ==================== LIFESPAN ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    print("\n" + "="*60)
    print("🚀 Starting Invoice Intelligence Agent")
    print("="*60)
    
    # Initialize database
    print("📊 Initializing database...")
    init_db()
    
    print("✅ Application ready!")
    print("="*60 + "\n")
    
    yield
    
    # Shutdown
    print("\n👋 Shutting down...")

# ==================== APP CREATION ====================

app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="AI-powered invoice processing and payment optimization",
    lifespan=lifespan
)

# ==================== MIDDLEWARE ====================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== ROUTES ====================

# Include routers
app.include_router(invoices_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")

# Root endpoint
@app.get("/")
async def root():
    """API information"""
    return {
        "name": settings.api_title,
        "version": settings.api_version,
        "description": "Invoice Intelligence Agent API",
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "invoices": "/api/v1/invoices",
            "chat": "/api/v1/chat"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "invoice-intelligence-agent",
        "version": settings.api_version
    }