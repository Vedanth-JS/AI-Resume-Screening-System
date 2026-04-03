import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta, timezone
import jwt
import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..db.database import get_db
from ..models.models import User, Role, Organization, user_roles, RoleEnum
from ..schemas.auth import Token, UserCreate, UserLogin
from ..core.config import settings
from ..core.sessions import session_manager
from ..core.logger import log

router = APIRouter(prefix="/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/token")

# ─── Auth Utils ─────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())

async def create_tokens(user: User, db: AsyncSession) -> Token:
    access_expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    roles = [r.name for r in user.roles]
    
    access_claims = {
        "sub": user.email,
        "org_id": user.org_id,
        "roles": roles,
        "exp": access_expire,
        "jti": str(uuid.uuid4())
    }
    
    refresh_claims = {
        "sub": user.email,
        "org_id": user.org_id,
        "exp": refresh_expire,
        "jti": str(uuid.uuid4())
    }
    
    access_token = jwt.encode(access_claims, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    refresh_token = jwt.encode(refresh_claims, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    # ─── Refresh Token Rotation (Hashed in DB) ──────────────────────────────
    user.refresh_token_hash = hash_password(refresh_token)
    await db.commit()
    
    # ─── Session Management (Redis) ──────────────────────────────────────────
    await session_manager.create_session(user.id, access_token, settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    
    return Token(access_token=access_token, refresh_token=refresh_token)

# ─── Auth Routes ────────────────────────────────────────────────────────────

from sqlalchemy.orm import selectinload

def get_current_user_with_role(required_role: RoleEnum):
    async def dependency(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            email: str = payload.get("sub")
            roles: list = payload.get("roles", [])
            # Role Hierarchy Logic:
            # ADMIN can access everything.
            # RECRUITER can access VIEWER routes.
            has_access = False
            if RoleEnum.ADMIN.value in roles:
                has_access = True
            elif required_role == RoleEnum.RECRUITER and RoleEnum.RECRUITER.value in roles:
                has_access = True
            elif required_role == RoleEnum.VIEWER and (RoleEnum.RECRUITER.value in roles or RoleEnum.VIEWER.value in roles):
                has_access = True
            elif not required_role:
                has_access = True

            if email is None or not has_access:
                log.warning("auth_forbidden", email=email, required=required_role, actual=roles)
                raise HTTPException(status.HTTP_403_FORBIDDEN, "Access forbidden")
        except HTTPException:
            # Re-raise HTTP exceptions (403, etc.) so they aren't swallowed by 401 block
            raise
        except jwt.ExpiredSignatureError:
            log.warning("auth_token_expired")
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token expired")
        except jwt.InvalidTokenError as e:
            log.warning("auth_token_invalid", error=str(e))
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")
        except Exception as e:
            log.error("auth_validation_error", error=str(e))
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Could not validate credentials")
            
        # ─── Session Check (Redis Blacklist) ──────────────────────────────────
        if await session_manager.is_blacklisted(token):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session invalidated")
            
        stmt = select(User).where(User.email == email).options(selectinload(User.roles))
        res = await db.execute(stmt)
        user = res.scalars().first()
        if not user:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
        return user
    return dependency

@router.post("/register")
async def register(data: UserCreate, db: AsyncSession = Depends(get_db)):
    # 1. Create Organization
    org = Organization(name=data.organization_name, slug=data.organization_slug)
    db.add(org)
    await db.flush()
    
    # 2. Check if user exists
    stmt = select(User).where(User.email == data.email)
    res = await db.execute(stmt)
    if res.scalars().first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email already exists")
    
    # 3. Create User
    new_user = User(
        email=data.email, 
        password_hash=hash_password(data.password),
        org_id=org.id
    )
    db.add(new_user)
    await db.flush()
    
    # 4. Assign RECRUITER role by default
    stmt = select(Role).where(Role.name == RoleEnum.RECRUITER)
    res = await db.execute(stmt)
    role = res.scalars().first()
    if role:
        # For Many-to-Many in async, we might need to handle this carefully if not loaded
        # But since it's a new user, we can just append
        new_user.roles.append(role)
        
    await db.commit()
    return {"status": "success", "user_id": new_user.id}

@router.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.email == form_data.username).options(selectinload(User.roles))
    res = await db.execute(stmt)
    user = res.scalars().first()
    
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    
    return await create_tokens(user, db)

@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_token: str, db: AsyncSession = Depends(get_db)):
    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email = payload.get("sub")
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
        
    stmt = select(User).where(User.email == email).options(selectinload(User.roles))
    res = await db.execute(stmt)
    user = res.scalars().first()
    
    if not user or not user.refresh_token_hash or not verify_password(refresh_token, user.refresh_token_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired session")
        
    return await create_tokens(user, db)

@router.post("/logout")
async def logout(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user_with_role(None))):
    # 1. Invalidate Access Token in Redis
    await session_manager.invalidate_session(token)
    
    # 2. Invalidate Refresh Token in DB
    current_user.refresh_token_hash = None
    await db.commit()
    
    return {"status": "success", "message": "Logged out"}
