from fastapi import APIRouter, Depends, HTTPException, status
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserLogin, TokenResponse
from app.services.auth_service import AuthService
from app.auth.jwt import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserCreate):
    """Register a new user"""
    return await AuthService.create_user(user_data)

@router.post("/login", response_model=TokenResponse)
async def login(login_data: UserLogin):
    """Login user and return JWT token"""
    return await AuthService.login_user(login_data.email, login_data.password)

@router.get("/profile", response_model=UserResponse)
async def get_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile"""
    return await AuthService.get_user_profile(str(current_user.id))

@router.put("/profile", response_model=UserResponse)
async def update_profile(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update current user profile"""
    return await AuthService.update_user_profile(str(current_user.id), user_data)

@router.post("/logout")
async def logout():
    """Logout user (client should discard token)"""
    return {"message": "Successfully logged out"}
