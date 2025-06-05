"""Request logging middleware."""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from datetime import datetime, UTC
import json
from models.models import RequestLog
from database import get_db
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request logging."""

    async def dispatch(self, request: Request, call_next):
        """Process the request and log it."""
        # Extract request payload safely
        payload = await self._extract_request_payload(request)
        
        # Create and save request log
        request_log = self._create_request_log(request, payload)
        await self._save_request_log(request_log)
        
        # Continue with the request
        response = await call_next(request)
        return response

    async def _extract_request_payload(self, request: Request) -> Dict[str, Any]:
        """Extract and parse the request payload without consuming it."""
        try:
            # Only try to read body for POST, PUT, PATCH requests
            if request.method in ["POST", "PUT", "PATCH"]:
                # Read the body but cache it so it's still available for the route
                body = await request.body()
                if body:
                    return json.loads(body)
            return {}
        except json.JSONDecodeError:
            logger.warning(f"Could not parse JSON body for {request.method} {request.url.path}")
            return {}
        except Exception as e:
            logger.error(f"Error extracting request payload: {e}")
            return {}

    def _create_request_log(self, request: Request, payload: Dict[str, Any]) -> RequestLog:
        """Create a new request log entry."""
        return RequestLog(
            method=request.method,
            path=request.url.path,
            payload=payload,
            timestamp=datetime.now(UTC)
        )

    async def _save_request_log(self, request_log: RequestLog) -> None:
        """Save the request log to the database."""
        try:
            db = next(get_db())
            db.add(request_log)
            db.commit()
            logger.info(f"Request logged: {request_log.method} {request_log.path}")
        except Exception as e:
            logger.error(f"Error saving request log: {e}")
        finally:
            if 'db' in locals():
                db.close() 