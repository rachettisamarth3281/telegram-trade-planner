import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.database import init_db, check_db_health
from app.utils.logging import setup_logging, get_logger
from app.api.v1.signals import router as signals_router
from app.api.v1.trade_plans import router as trade_plans_router
from app.api.v1.trades import router as trades_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.market import router as market_router
from app.api.v1.settings import router as settings_router
from app.api.telegram_routes import router as telegram_router
from app.api.websockets import ws_manager
from app.telegram import telegram_service

setup_logging(log_level=settings.LOG_LEVEL, json_logs=settings.JSON_LOGS)
logger = get_logger("app.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing database schema and indexes...")
    await init_db()

    # Start Telegram Listener service (starts listening if credentials present, or registers in mock/standby mode)
    asyncio.create_task(telegram_service.start())

    yield

    # Shutdown
    await telegram_service.stop()
    logger.info("Application shutdown complete.")

app = FastAPI(
    title=settings.APP_NAME,
    version="2.0.0",
    description="Paper Trading Signal Analysis System for Telegram trading channels (Phase 2 - Telegram Ingestion)",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(telegram_router, prefix="/api/v1")
app.include_router(signals_router, prefix="/api/v1")
app.include_router(trade_plans_router, prefix="/api/v1")
app.include_router(trades_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(market_router, prefix="/api/v1")
app.include_router(settings_router, prefix="/api/v1")

@app.websocket("/api/v1/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)

@app.get("/health")
@app.get("/api/health")
async def health_check():
    db_healthy = await check_db_health()
    return {
        "status": "healthy" if db_healthy else "unhealthy",
        "database": "connected" if db_healthy else "disconnected",
        "app": settings.APP_NAME,
        "env": settings.APP_ENV,
        "mode": "PAPER_TRADING_ONLY",
        "telegram": telegram_service.get_status()
    }

# Mount static frontend build if present
frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))
if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="static")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        if full_path.startswith("api") or full_path.startswith("ws"):
            return None
        index_file = os.path.join(frontend_dist, "index.html")
        return FileResponse(index_file)
