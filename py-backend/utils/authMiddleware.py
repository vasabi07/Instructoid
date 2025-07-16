from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from jose import jwt, JWTError
import requests

def get_jwks():
    """Fetch JWKS dynamically to avoid startup issues"""
    try:
        response = requests.get("http://localhost:3000/api/auth/jwks", timeout=5)
        return response.json()
    except Exception as e:
        print(f"Failed to fetch JWKS: {e}")
        return None

def verify_jwt(token: str):
    try:
        jwks = get_jwks()
        if not jwks:
            print("JWKS not available")
            return None
            
        payload = jwt.decode(
            token, 
            jwks, 
            algorithms=["ES256"],
            issuer="http://localhost:3000",
            audience="http://localhost:3000",
        )
        return payload
    except JWTError as e:
        print(f"JWT verification failed: {e}")
        return None


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.method == "OPTIONS":
            response = await call_next(request)
            return response
        
        # Skip authentication for root endpoint
        if request.url.path == "/":
            response = await call_next(request)
            return response
        auth: str | None = request.headers.get("Authorization")
        if not auth or not auth.startswith("Bearer "):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        token = auth.split(" ")[1]
        payload = verify_jwt(token)
        if not payload:
            return JSONResponse({"error": "Invalid token"}, status_code=401)
        request.state.user = payload  
        response = await call_next(request)
        return response
        
