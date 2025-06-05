from fastapi import APIRouter
from datetime import datetime

router = APIRouter(prefix="/v1/health", tags=["Health Check"])


@router.get("")
async def health_check():
    """Endpoint para verificar el estado del servicio"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
    }
