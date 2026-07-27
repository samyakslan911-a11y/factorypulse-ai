from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.db.client import get_db

_security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(_security)) -> str:
    try:
        client = get_db()
        response = client.auth.get_user(credentials.credentials)
        return response.user.id
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
