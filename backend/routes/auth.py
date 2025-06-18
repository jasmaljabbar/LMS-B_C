# backend/routes/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta, datetime
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import os
import logging

from backend import models, schemas, utils
from backend.database import get_db
from backend.logger_utils import log_activity
from backend.dependencies import get_current_user

load_dotenv()
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/login", response_model=schemas.UserInfo)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    """Handles user login, updates last_login time, and logs the activity."""
    
    # Find user by username
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    
    if not user:
        # Log failed login attempt for non-existent user (optional - be careful about revealing info)
        logger.warning(f"Login attempt for non-existent username: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Verify password
    if not utils.verify_password(form_data.password, user.password_hash):
        # Log failed login attempt for existing user
        log_activity(
            db=db, 
            user_id=None,  # No user_id since login failed
            action='LOGIN_FAILED', 
            details=f"Failed password attempt for user: {user.username} (ID: {user.id})", 
            target_entity='User', 
            target_entity_id=user.id
        )
        logger.warning(f"Failed password attempt for user: {user.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Update last login time and log successful login
    try:
        user.last_login = datetime.utcnow()
        db.commit()
        db.refresh(user)
        logger.info(f"Updated last_login for user: {user.username}")

        # Log successful login after successful commit of last_login
        log_activity(
            db=db,
            user_id=user.id,
            action='USER_LOGIN',
            details=f"User '{user.username}' logged in successfully.",
            target_entity='User',
            target_entity_id=user.id
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update last_login or log activity for user {user.username}: {e}", exc_info=True)
        # Don't prevent login if only logging fails - the user did authenticate successfully

    # Generate JWT token
    jwt_expiry_minutes = int(os.getenv("JWT_EXPIRY_MINUTES", "30"))  # Increased default from 15 to 30
    access_token_expires = timedelta(minutes=jwt_expiry_minutes)
    access_token = utils.create_access_token(
        subject=user.username, 
        expires_delta=access_token_expires
    )

    # Determine entity ID based on user type
    entity_id = None
    try:
        if user.user_type == "Teacher":
            teacher = db.query(models.Teacher.id).filter(models.Teacher.user_id == user.id).first()
            entity_id = teacher.id if teacher else None
            
        elif user.user_type == "Student":
            student = db.query(models.Student.id).filter(models.Student.user_id == user.id).first()
            entity_id = student.id if student else None
            
        elif user.user_type == "Parent":
            parent = db.query(models.Parent.id).filter(models.Parent.user_id == user.id).first()
            entity_id = parent.id if parent else None
            
        elif user.user_type == "Admin":
            entity_id = user.id  # Use user ID itself for Admin
            
    except Exception as e:
        # Don't fail login if entity lookup fails, but log the issue
        logger.error(f"Error determining entity_id for user {user.username}: {e}", exc_info=True)
        entity_id = None

    # Log warning if entity ID couldn't be determined (except for Admin which uses user.id)
    if entity_id is None and user.user_type != 'Admin':
        logger.warning(f"Could not determine entity_id for user {user.username} (Type: {user.user_type})")

    # Return successful login response
    return schemas.UserInfo(
        user_id=user.id,
        user_type=user.user_type,
        entity_id=entity_id,
        access_token=access_token,
        token_type="bearer",
        photo=user.photo
    )

@router.post("/logout")
def logout(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Handles user logout and logs the activity.
    Note: JWT tokens are stateless, so this mainly serves for logging purposes.
    Client should discard the token.
    """
    try:
        log_activity(
            db=db,
            user_id=current_user.id,
            action='USER_LOGOUT',
            details=f"User '{current_user.username}' logged out.",
            target_entity='User',
            target_entity_id=current_user.id
        )
        logger.info(f"User {current_user.username} logged out")
        
        return {"message": "Successfully logged out"}
        
    except Exception as e:
        logger.error(f"Error logging logout for user {current_user.username}: {e}", exc_info=True)
        return {"message": "Logged out (logging failed)"}

@router.get("/me", response_model=schemas.UserInfo)  # Assuming you have a UserProfile schema
def get_current_user_info(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed information about the currently logged-in user."""
    try:
        # You might want to return more detailed user information
        # This is just a basic example
        return {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "user_type": current_user.user_type,
            "photo": current_user.photo,
            "created_at": current_user.created_at,
            "last_login": current_user.last_login,
            "is_active": current_user.is_active
        }
    except Exception as e:
        logger.error(f"Error fetching user profile for {current_user.username}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching user profile")

@router.post("/refresh-token", response_model=schemas.TokenData)  # Assuming you have this schema
def refresh_access_token(
    current_user: models.User = Depends(get_current_user)
):
    """
    Refresh the access token for the current user.
    This can be useful for extending sessions without full re-authentication.
    """
    try:
        jwt_expiry_minutes = int(os.getenv("JWT_EXPIRY_MINUTES", "30"))
        access_token_expires = timedelta(minutes=jwt_expiry_minutes)
        new_access_token = utils.create_access_token(
            subject=current_user.username, 
            expires_delta=access_token_expires
        )
        
        logger.info(f"Refreshed token for user: {current_user.username}")
        
        return {
            "access_token": new_access_token,
            "token_type": "bearer",
            "expires_in": jwt_expiry_minutes * 60  # Return expiry in seconds
        }
        
    except Exception as e:
        logger.error(f"Error refreshing token for user {current_user.username}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error refreshing token")