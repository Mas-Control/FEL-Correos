from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from health_check.routers import health_check
from invoices.routers import invoices
from auth.routers import auth
from users.routers import users
from middlewares.auth_and_logging import RequestLoggingMiddleware

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SAT Invoices Processor",
    description="Digital SAT's invoices processor",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)

logger.info("Registering API routes...")

try:
    app.include_router(health_check.router)
    app.include_router(invoices.router)
    app.include_router(auth.router)
    app.include_router(users.router)
except Exception as e:
    logger.error("Error registering API routes: %s", str(e))
    raise

logger.info("Initialization completed successfully")
