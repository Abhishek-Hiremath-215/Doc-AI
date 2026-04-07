import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from typing import Generator, Optional
from uuid import UUID
from datetime import datetime, timedelta
from passlib.context import CryptContext

from database import SessionLocal
from models import User
from core.config import SECRET_KEY, ALGORITHM
from core.role_enum import UserRole

# Fixed OAuth2 scheme to match your login endpoint
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")

logger = logging.getLogger("uvicorn")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# Database dependency
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# JWT Token Creation
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 1 week
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Current user dependencies
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    logger.info(f"🔍 Token received: {token[:20]}..." if token else "No token")
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not token:
        logger.error("❌ No token provided")
        raise credentials_exception
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str = payload.get("sub")
        if not user_id_str:
            logger.error("❌ No 'sub' in token payload")
            raise credentials_exception
        user_id = UUID(user_id_str)
        logger.info(f"✅ Token decoded successfully, user_id: {user_id}")
    except (JWTError, ValueError) as e:
        logger.error(f"❌ JWT decode error: {e}")
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.error(f"❌ User not found with id {user_id}")
        raise credentials_exception
    
    if not user.is_active:
        logger.error(f"❌ User {user.email} is inactive")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive")
    
    logger.info(f"✅ User authenticated: {user.email} with role {user.role}")
    return user

def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Any active user role"""
    logger.info(f"🔍 Checking active user: {current_user.email} with role {current_user.role}")
    
    allowed_roles = [
        UserRole.user, UserRole.consultant, UserRole.manager,
        UserRole.finance, UserRole.orgadmin, UserRole.superadmin
    ]
    
    if current_user.role not in allowed_roles:
        logger.error(f"❌ User role {current_user.role} not in allowed roles {allowed_roles}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized user")
    
    logger.info(f"✅ User {current_user.email} is active with valid role")
    return current_user

def get_current_org_admin(current_user: User = Depends(get_current_user)) -> User:
    """Org admin only"""
    if current_user.role != UserRole.orgadmin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Org admin privileges required")
    return current_user

def get_current_super_admin(current_user: User = Depends(get_current_user)) -> User:
    """Super admin only"""
    if current_user.role != UserRole.superadmin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super admin privileges required")
    return current_user

# Generic role-based checker
def require_roles(*allowed_roles: UserRole):
    """Use as Depends(require_roles(UserRole.superadmin)) to enforce roles"""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            logger.warning(
                f"User {current_user.email} with role {current_user.role} "
                f"tried to access but required one of {allowed_roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {', '.join([r.value for r in allowed_roles])}"
            )
        return current_user
    return role_checker

# Service dependencies (if you're using them)
try:
    from services import UserService, ProjectService, OrganizationService, FileService

    def get_user_service(db: Session = Depends(get_db)) -> UserService:
        return UserService(db)

    def get_project_service(db: Session = Depends(get_db)) -> ProjectService:
        return ProjectService(db)

    def get_organization_service(db: Session = Depends(get_db)) -> OrganizationService:
        return OrganizationService(db)

    def get_file_service(db: Session = Depends(get_db)) -> FileService:
        return FileService(db)
except ImportError:
    # Services not available, skip these dependencies
    pass
