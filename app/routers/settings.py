from fastapi import APIRouter, Depends, status
from typing import Dict
from app.models.user import User
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService
from app.auth.jwt import get_current_user

router = APIRouter(prefix="/settings", tags=["Settings"])

@router.get("/", response_model=Dict)
async def get_settings(current_user: User = Depends(get_current_user)):
    """Get user settings"""
    return current_user.settings

@router.put("/", response_model=UserResponse)
async def update_settings(
    settings: Dict,
    current_user: User = Depends(get_current_user)
):
    """Update user settings"""
    from app.schemas.user import UserUpdate
    user_data = UserUpdate(settings=settings)
    return await AuthService.update_user_profile(str(current_user.id), user_data)
