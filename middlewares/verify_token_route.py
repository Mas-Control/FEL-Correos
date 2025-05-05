"""Verify token route middleware."""

from fastapi import Request
from fastapi.routing import APIRoute
from fastapi.responses import JSONResponse
from core.security import get_current_accountant


class VerifyTokenRoute(APIRoute):
    """Verify token route middleware."""

    def get_route_handler(self):
        original_route = super().get_route_handler()

        async def verify_token_middleware(request: Request):
            # Check if Authorization header exists
            if "Authorization" not in request.headers:
                return JSONResponse(
                    status_code=401,
                    content={
                        "message": (
                            "Unauthorized - Missing Authorization header"
                        )
                    },
                )

            try:
                token = request.headers["Authorization"].split(" ")[1]
            except IndexError:
                return JSONResponse(
                    status_code=401,
                    content={
                        "message": (
                            "Unauthorized - Invalid Authorization format"
                        )
                    },
                )

            if not token:
                return JSONResponse(
                    status_code=401,
                    content={
                        "message": "Unauthorized - Missing token"
                    },
                )

            user_response = await get_current_accountant(token=token)
            if not user_response:
                print("user_response is none")
                return user_response
            print("user_response", user_response)
            return await original_route(request)

        return verify_token_middleware
