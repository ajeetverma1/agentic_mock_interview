from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.interview import router as interview_router
from app.config import (
    CORS_ORIGINS,
    ENVIRONMENT,
    DEBUG,
    API_TITLE,
    API_VERSION,
    API_DESCRIPTION,
    API_V1_PREFIX
)
import logging
import time

# Configure logging
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
    debug=DEBUG,
    docs_url="/docs" if ENVIRONMENT != "production" else None,  # Disable docs in production
    redoc_url="/redoc" if ENVIRONMENT != "production" else None,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with timing information."""
    start_time = time.time()
    
    # Log request
    logger.info(f"Request: {request.method} {request.url.path}")
    
    try:
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log response
        logger.info(
            f"Response: {request.method} {request.url.path} "
            f"Status: {response.status_code} "
            f"Duration: {process_time:.3f}s"
        )
        
        # Add custom headers
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
    
    except Exception as e:
        logger.error(f"Request failed: {request.method} {request.url.path} - {str(e)}")
        raise


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions gracefully."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal server error occurred" if ENVIRONMENT == "production" else str(exc),
            "type": "internal_server_error"
        }
    )


# Include routers
app.include_router(interview_router, prefix=API_V1_PREFIX, tags=["interview"])


# Root endpoint
@app.get("/")
def root():
    """API root endpoint with service information."""
    return {
        "service": "Mock Interview Agent API",
        "version": API_VERSION,
        "environment": ENVIRONMENT,
        "status": "running",
        "endpoints": {
            "start_interview": f"{API_V1_PREFIX}/interview/start",
            "voice_message": f"{API_V1_PREFIX}/interview/voice",
            "text_message": f"{API_V1_PREFIX}/interview/text",
            "get_feedback": f"{API_V1_PREFIX}/interview/{{session_id}}/feedback",
            "get_session": f"{API_V1_PREFIX}/interview/{{session_id}}",
            "end_interview": f"{API_V1_PREFIX}/interview/{{session_id}}/end",
            "active_sessions": f"{API_V1_PREFIX}/interview/sessions/active",
            "health": "/health",
            "docs": "/docs" if ENVIRONMENT != "production" else "disabled in production"
        }
    }


# Health check endpoint
@app.get("/health")
def health_check():
    """Health check endpoint for monitoring and load balancers."""
    return {
        "status": "healthy",
        "environment": ENVIRONMENT,
        "version": API_VERSION,
        "timestamp": time.time()
    }


# Readiness check endpoint
@app.get("/ready")
def readiness_check():
    """Readiness check endpoint for Kubernetes/deployment platforms."""
    try:
        # Check if critical services are ready
        # Add checks for database, Redis, etc. when implemented
        from app.config import GOOGLE_API_KEY
        
        if not GOOGLE_API_KEY:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "not_ready",
                    "reason": "GOOGLE_API_KEY not configured"
                }
            )
        
        return {
            "status": "ready",
            "environment": ENVIRONMENT,
            "version": API_VERSION
        }
    
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "reason": str(e) if ENVIRONMENT != "production" else "Service unavailable"
            }
        )


# Startup event
@app.on_event("startup")
async def startup_event():
    """Execute startup tasks."""
    logger.info(f"Starting {API_TITLE} v{API_VERSION}")
    logger.info(f"Environment: {ENVIRONMENT}")
    logger.info(f"Debug mode: {DEBUG}")
    
    # Validate configuration
    from app.config import GOOGLE_API_KEY
    if not GOOGLE_API_KEY:
        logger.error("GOOGLE_API_KEY not found! Application may not function correctly.")
    else:
        logger.info("Google API Key configured successfully")
    
    # Initialize services
    logger.info("Initializing LangGraph agent...")
    try:
        from app.agent.interview_agent import interview_agent
        logger.info("LangGraph agent initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize LangGraph agent: {e}")
    
    logger.info("Application startup complete")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Execute cleanup tasks on shutdown."""
    logger.info("Shutting down application...")
    
    # Clean up resources
    # Close database connections, clear caches, etc.
    
    logger.info("Application shutdown complete")


if __name__ == "__main__":
    import uvicorn
    
    # Run the application
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8002,
        reload=DEBUG,  # Auto-reload in development
        log_level="info" if DEBUG else "warning"
    )
