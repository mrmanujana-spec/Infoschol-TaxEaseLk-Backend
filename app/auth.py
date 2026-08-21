"""
Every request from the UI carries a Supabase login token in the header:
    Authorization: Bearer <token>

This file checks that token is real, then hands back who's making the
request. This build only has ONE role in play -- "auditor" -- since
that's the only workspace you've shown me so far. Set it on each
auditor user via Supabase dashboard -> Authentication -> user ->
Raw App Meta Data -> {"role": "auditor"}
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

from app.config import SUPABASE_JWT_SECRET

bearer_scheme = HTTPBearer()


class CurrentUser:
    def __init__(self, user_id: str, email: str, role: str):
        self.user_id = user_id
        self.email = email
        self.role = role


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> CurrentUser:
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token, SUPABASE_JWT_SECRET, algorithms=["HS256"], audience="authenticated"
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token. Please log in again.",
        )

    user_id = payload.get("sub")
    email = payload.get("email", "")
    role = payload.get("app_metadata", {}).get("role")

    if not user_id or not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is missing required user info (id or role).",
        )
    return CurrentUser(user_id=user_id, email=email, role=role)


def require_role(*allowed_roles: str):
    def role_checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Your role ('{user.role}') is not allowed to do this.",
            )
        return user

    return role_checker
