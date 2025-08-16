from datetime import datetime
from typing import Optional
from fastapi import HTTPException, status
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.auth.jwt import get_password_hash, verify_password, create_access_token
from bson import ObjectId

class AuthService:
    @staticmethod
    async def create_user(user_data: UserCreate) -> UserResponse:
        """Create a new user"""
        # Check if user already exists
        existing_user = await User.find_one({"email": user_data.email})
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Hash password and create user
        hashed_password = get_password_hash(user_data.password)
        user = User(
            name=user_data.name,
            email=user_data.email,
            password=hashed_password,
            avatar=user_data.avatar,
            settings=user_data.settings or {}
        )
        
        await user.insert()
        return UserResponse(
            id=str(user.id),
            name=user.name,
            email=user.email,
            avatar=user.avatar,
            settings=user.settings,
            createdAt=user.createdAt,
            updatedAt=user.updatedAt
        )

    @staticmethod
    async def authenticate_user(email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password"""
        user = await User.find_one({"email": email})
        if not user:
            return None
        
        if not verify_password(password, user.password):
            return None
        
        return user

    @staticmethod
    async def login_user(email: str, password: str) -> dict:
        """Login user and return token"""
        user = await AuthService.authenticate_user(email, password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Create access token
        access_token = create_access_token(data={"sub": str(user.id)})
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": UserResponse(
                id=str(user.id),
                name=user.name,
                email=user.email,
                avatar=user.avatar,
                settings=user.settings,
                createdAt=user.createdAt,
                updatedAt=user.updatedAt
            )
        }

    @staticmethod
    async def get_user_profile(user_id: str) -> UserResponse:
        """Get user profile by ID"""
        try:
            user = await User.get(ObjectId(user_id))
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            return UserResponse(
                id=str(user.id),
                name=user.name,
                email=user.email,
                avatar=user.avatar,
                settings=user.settings,
                createdAt=user.createdAt,
                updatedAt=user.updatedAt
            )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

    @staticmethod
    async def update_user_profile(user_id: str, user_data: UserUpdate) -> UserResponse:
        """Update user profile"""
        try:
            user = await User.get(ObjectId(user_id))
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Update fields if provided
            update_data = {}
            if user_data.name is not None:
                update_data["name"] = user_data.name
            if user_data.avatar is not None:
                update_data["avatar"] = user_data.avatar
            if user_data.settings is not None:
                update_data["settings"] = user_data.settings
            
            update_data["updatedAt"] = datetime.utcnow()
            
            await user.update({"$set": update_data})
            
            # Get updated user
            updated_user = await User.get(ObjectId(user_id))
            return UserResponse(
                id=str(updated_user.id),
                name=updated_user.name,
                email=updated_user.email,
                avatar=updated_user.avatar,
                settings=updated_user.settings,
                createdAt=updated_user.createdAt,
                updatedAt=updated_user.updatedAt
            )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
