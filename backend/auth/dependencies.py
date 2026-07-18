from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client
from backend.config import settings

_security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(_security)) -> str:
    try:
        client = create_client(settings.supabase_url, settings.supabase_key)
        response = client.auth.get_user(credentials.credentials)
        return response.user.id
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
