from fastapi import Request, HTTPException, status
import jwt
from ..core.config import settings

async def multi_tenant_middleware(request: Request, call_next):
    # Skip for public routes
    if request.url.path.startswith("/api/auth") or request.url.path in ["/docs", "/redoc", "/openapi.json"]:
        return await call_next(request)
    
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        # If no token, we can't inject org_id, but the route might still be protected by a dependency
        return await call_next(request)
    
    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        request.state.org_id = payload.get("org_id")
        request.state.user_email = payload.get("sub")
        request.state.roles = payload.get("roles", [])
    except Exception:
        # Invalid token - let the Auth dependencies handle the error response
        pass
    
    response = await call_next(request)
    return response
