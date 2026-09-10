import time
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.config import settings
from app.database import init_db
from app.routers import (
    availability_router,
    reservations_router,
    vendor_router,
    websocket_router
)

# Configure structured logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("oasis.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown lifecycle manager."""
    logger.info(f"Starting {settings.APP_NAME} in [{settings.ENV}] mode...")
    await init_db()
    logger.info("Database initialized successfully.")
    yield
    logger.info("Shutting down Oasis Backend...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="High-concurrency B2B Restaurant Reservation & Inventory Management Engine for Tashkent dining establishments.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# 1. Strict CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Process-Time"]
)


# 2. Process Time & Request Logging Middleware
@app.middleware("http")
async def process_time_logging_middleware(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time_ms = (time.perf_counter() - start_time) * 1000
    response.headers["X-Process-Time"] = f"{process_time_ms:.2f}ms"

    logger.info(
        f"{request.method} {request.url.path} "
        f"-> Status: {response.status_code} "
        f"| Latency: {process_time_ms:.2f}ms"
    )
    return response


# 3. Global Exception Handlers for Uniform JSON Error Responses
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    code_mapping = {
        status.HTTP_400_BAD_REQUEST: "BAD_REQUEST",
        status.HTTP_401_UNAUTHORIZED: "UNAUTHORIZED",
        status.HTTP_403_FORBIDDEN: "FORBIDDEN",
        status.HTTP_404_NOT_FOUND: "NOT_FOUND",
        status.HTTP_409_CONFLICT: "CONFLICT",
        status.HTTP_422_UNPROCESSABLE_ENTITY: "UNPROCESSABLE_ENTITY"
    }
    error_code = code_mapping.get(exc.status_code, "HTTP_ERROR")

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": error_code,
                "message": exc.detail,
                "status_code": exc.status_code,
                "path": request.url.path
            }
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid request parameters or payload format.",
                "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
                "details": exc.errors(),
                "path": request.url.path
            }
        }
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled Exception on {request.url.path}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected server error occurred. Please try again later.",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "path": request.url.path
            }
        }
    )


# 4. Root & Health Check Endpoints
@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENV
    }


# 5. Include API Routers
app.include_router(availability_router, prefix="/api/v1")
app.include_router(reservations_router, prefix="/api/v1")
app.include_router(vendor_router, prefix="/api/v1")
app.include_router(websocket_router)
