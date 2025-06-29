"""
JWT Authentication Endpoints

Provides REST API endpoints for JWT authentication including:
- User login and token generation
- Token refresh
- User profile management
- Authentication status checks

Author: Distinguished Cyber Security Engineer
Date: 2025-06-29
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field

from .jwt_auth import jwt_auth, JWTUser, UserRole

logger = logging.getLogger(__name__)

# Create router for JWT endpoints
jwt_router = APIRouter(prefix="/auth", tags=["JWT Authentication"])

# Bearer token security
security = HTTPBearer()


# Request/Response Models
class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Dict[str, Any]


class RefreshRequest(BaseModel):
    refresh_token: str


class UserProfileResponse(BaseModel):
    user_id: str
    username: str
    email: str = None
    role: str
    permissions: list[str]
    is_active: bool
    created_at: datetime
    last_login: datetime = None


class AuthStatusResponse(BaseModel):
    authenticated: bool
    user: UserProfileResponse = None
    token_valid: bool = False
    expires_at: datetime = None


# Authentication Endpoints

@jwt_router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Authenticate user and return JWT tokens
    
    Provides both access and refresh tokens for authenticated users.
    Access token expires in 60 minutes, refresh token in 7 days.
    """
    try:
        # Authenticate user
        user = jwt_auth.authenticate_user(request.username, request.password)
        if not user:
            logger.warning(f"Login attempt failed for username: {request.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password"
            )
        
        # Generate tokens
        access_token = jwt_auth.create_access_token(user)
        refresh_token = jwt_auth.create_refresh_token(user)
        
        logger.info(f"User logged in successfully: {user.username} (role: {user.role})")
        
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=jwt_auth.access_token_expire_minutes * 60,
            user={
                "user_id": user.user_id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "permissions": user.permissions,
                "last_login": user.last_login.isoformat() if user.last_login else None
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error for username {request.username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed due to server error"
        )


@jwt_router.post("/refresh", response_model=LoginResponse)
async def refresh_token(request: RefreshRequest):
    """
    Refresh access token using refresh token
    
    Allows clients to obtain new access tokens without re-authentication.
    """
    try:
        # Verify refresh token
        token_data = jwt_auth.verify_token(request.refresh_token)
        
        # Get user
        user = jwt_auth.get_user_by_id(token_data.user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Generate new tokens
        access_token = jwt_auth.create_access_token(user)
        refresh_token = jwt_auth.create_refresh_token(user)
        
        logger.info(f"Token refreshed for user: {user.username}")
        
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=jwt_auth.access_token_expire_minutes * 60,
            user={
                "user_id": user.user_id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "permissions": user.permissions,
                "last_login": user.last_login.isoformat() if user.last_login else None
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token refresh failed"
        )


@jwt_router.get("/me", response_model=UserProfileResponse)
async def get_user_profile(request: Request):
    """
    Get current user profile
    
    Returns detailed information about the authenticated user.
    """
    try:
        user = await jwt_auth.get_current_user(request)
        
        return UserProfileResponse(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            role=user.role,
            permissions=user.permissions,
            is_active=user.is_active,
            created_at=user.created_at,
            last_login=user.last_login
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user profile"
        )


@jwt_router.get("/status", response_model=AuthStatusResponse)
async def get_auth_status(request: Request):
    """
    Check authentication status
    
    Returns whether the current request is authenticated and token details.
    """
    try:
        # Try to get current user
        user = await jwt_auth.get_current_user(request)
        
        # Extract token expiry from Authorization header
        authorization = request.headers.get("Authorization", "")
        expires_at = None
        token_valid = False
        
        if authorization.startswith("Bearer "):
            token = authorization.split(" ")[1]
            try:
                token_data = jwt_auth.verify_token(token)
                expires_at = token_data.expires_at
                token_valid = True
            except:
                pass
        
        return AuthStatusResponse(
            authenticated=True,
            user=UserProfileResponse(
                user_id=user.user_id,
                username=user.username,
                email=user.email,
                role=user.role,
                permissions=user.permissions,
                is_active=user.is_active,
                created_at=user.created_at,
                last_login=user.last_login
            ),
            token_valid=token_valid,
            expires_at=expires_at
        )
        
    except HTTPException:
        # User not authenticated
        return AuthStatusResponse(
            authenticated=False,
            token_valid=False
        )
    except Exception as e:
        logger.error(f"Error checking auth status: {e}")
        return AuthStatusResponse(
            authenticated=False,
            token_valid=False
        )


@jwt_router.get("/users")
async def list_users(request: Request):
    """
    List all users (Admin only)
    
    Returns list of all users in the system. Requires admin role.
    """
    try:
        user = await jwt_auth.get_current_user(request)
        
        # Check admin permission
        if not jwt_auth.check_role_permission(user.role, UserRole.ADMIN):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin role required"
            )
        
        users = []
        for u in jwt_auth.users.values():
            users.append({
                "user_id": u.user_id,
                "username": u.username,
                "email": u.email,
                "role": u.role,
                "permissions": u.permissions,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat(),
                "last_login": u.last_login.isoformat() if u.last_login else None
            })
        
        return {
            "users": users,
            "total": len(users)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list users"
        )


@jwt_router.get("/stats")
async def get_auth_stats():
    """
    Get authentication statistics
    
    Returns comprehensive statistics about the JWT authentication system.
    """
    try:
        stats = jwt_auth.get_security_stats()
        
        # Add timestamp
        stats["timestamp"] = datetime.now(timezone.utc).isoformat()
        stats["system_info"] = {
            "component": "Core Nexus Memory Service",
            "security_level": "Enterprise JWT + RBAC",
            "version": "1.0.0"
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting auth stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get authentication statistics"
        )


@jwt_router.post("/logout")
async def logout(request: Request):
    """
    Logout user
    
    Note: JWT tokens are stateless, so logout is primarily for client-side cleanup.
    In production, you might want to implement token blacklisting.
    """
    try:
        user = await jwt_auth.get_current_user(request)
        
        logger.info(f"User logged out: {user.username}")
        
        return {
            "message": "Logged out successfully",
            "username": user.username,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        # Allow logout even if token is invalid
        return {
            "message": "Logged out successfully",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error during logout: {e}")
        return {
            "message": "Logged out successfully",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# FastAPI dependency for getting current user
async def get_current_user(request: Request) -> JWTUser:
    """FastAPI dependency to get current authenticated user"""
    return await jwt_auth.get_current_user(request)


# FastAPI dependency for requiring admin role
async def require_admin_user(user: JWTUser = Depends(get_current_user)) -> JWTUser:
    """FastAPI dependency to require admin role"""
    if not jwt_auth.check_role_permission(user.role, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )
    return user


# FastAPI dependency for requiring user role or higher
async def require_user_role(user: JWTUser = Depends(get_current_user)) -> JWTUser:
    """FastAPI dependency to require user role or higher"""
    if not jwt_auth.check_role_permission(user.role, UserRole.USER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User role or higher required"
        )
    return user


# FastAPI dependency for requiring read-only role or higher
async def require_read_access(user: JWTUser = Depends(get_current_user)) -> JWTUser:
    """FastAPI dependency to require read-only role or higher"""
    if not jwt_auth.check_role_permission(user.role, UserRole.READ_ONLY):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Read access required"
        )
    return user