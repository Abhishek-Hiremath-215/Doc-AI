from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID
import logging
from passlib.context import CryptContext

from core.role_enum import UserRole
from core.config import SECRET_KEY, ALGORITHM
from database import SessionLocal
from models import User

logger = logging.getLogger("uvicorn")

# ==========================
# OAuth2 Password Bearer
# ==========================
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login", auto_error=False)
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 1 week

# ==========================
# Password Hashing
# ==========================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# ==========================
# DB Dependency
# ==========================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==========================
# JWT Token Creation
# ==========================
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# ==========================
# Current User Dependencies
# ==========================
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not token:
        raise credentials_exception
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise credentials_exception
        user_id = UUID(user_id_str)
    except (JWTError, ValueError) as e:
        logger.warning(f"JWT decode error: {e}")
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise credentials_exception
    
    print(f"✅ User authenticated: {user.email} (role: {user.role})")
    return user

async def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme), 
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Get current user if authenticated, otherwise return None"""
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str = payload.get("sub")
        if not user_id_str:
            return None
        user_id = UUID(user_id_str)
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            return None
        
        return user
    except (JWTError, ValueError):
        return None

# ==========================
# Role-based Dependencies
# ==========================
def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require superadmin or orgadmin role"""
    if current_user.role not in [UserRole.superadmin, UserRole.orgadmin]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Admin privileges required."
        )
    return current_user

def require_superadmin(current_user: User = Depends(get_current_user)) -> User:
    """Require superadmin role only"""
    if current_user.role != UserRole.superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Super Admin privileges required."
        )
    return current_user

def require_orgadmin_with_org(current_user: User = Depends(get_current_user)) -> User:
    """Require orgadmin role and ensure they belong to an organization"""
    if current_user.role != UserRole.orgadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Organization admin role required."
        )
    
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization admin must belong to an organization."
        )
    
    return current_user

def require_roles(*allowed_roles: UserRole):
    """Create dependency that checks for specific roles"""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            print(f"❌ Role check failed - User {current_user.email} has role {current_user.role}, required: {allowed_roles}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail=f"Insufficient privileges. Required roles: {[role.value for role in allowed_roles]}"
            )
        return current_user
    return role_checker
