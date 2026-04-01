from fastapi import Header, HTTPException, status
from api.firebase_utils import verify_firebase_token, get_user_role

async def get_current_user(authorization: str = Header(...)) -> dict:
    """
    Extract and verify Firebase ID token from Authorization: Bearer <token> header.
    Returns decoded token dict with uid, email, and role.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Use: Bearer <token>"
        )
    token = authorization.split(" ", 1)[1]
    try:
        decoded = verify_firebase_token(token)
        uid = decoded.get("uid")
        role = get_user_role(uid)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User has no assigned role."
            )
        decoded["role"] = role
        return decoded
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {str(e)}"
        )

def require_role(*roles):
    """Dependency factory: raise 403 if user's role is not in the allowed list."""
    async def checker(current_user: dict = None):
        if current_user.get("role") not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role(s): {', '.join(roles)}"
            )
        return current_user
    return checker
