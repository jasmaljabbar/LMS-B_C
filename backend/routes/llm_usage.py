# backend/routes/llm_usage.py
from fastapi import APIRouter, Depends, HTTPException, Query, status # Added status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date, timedelta

from backend.database import get_db
from backend.models import LLMTokenUsage, User
from backend.schemas import LLMTokenUsageInfo, LLMTokenUsageCreate
from backend.dependencies import get_current_user

router = APIRouter(
    tags=["LLM Token Usage"]
)

@router.get("/me/", response_model=List[LLMTokenUsageInfo])
def read_own_llm_token_usage(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    start_date: Optional[date] = Query(None, description="Filter by start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Filter by end date (YYYY-MM-DD)")
):
    """
    Retrieve LLM token usage for the currently authenticated user.
    """
    query = db.query(LLMTokenUsage).filter(LLMTokenUsage.user_id == current_user.id)

    if start_date:
        query = query.filter(LLMTokenUsage.timestamp >= datetime.combine(start_date, datetime.min.time()))

    if end_date:
        query = query.filter(LLMTokenUsage.timestamp < datetime.combine(end_date + timedelta(days=1), datetime.min.time()))

    token_usages = query.order_by(LLMTokenUsage.timestamp.desc()).all()
    return token_usages

@router.get("/user/{user_id}/", response_model=List[LLMTokenUsageInfo])
def read_user_llm_token_usage_by_admin(
    user_id: int,
    admin_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    start_date: Optional[date] = Query(None, description="Filter by start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Filter by end date (YYYY-MM-DD)")
):
    """
    Retrieve LLM token usage for a specific user. Admin access required.
    """
    if admin_user.user_type != "Admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized. Admin access required.")

    query = db.query(LLMTokenUsage).filter(LLMTokenUsage.user_id == user_id)

    if start_date:
        query = query.filter(LLMTokenUsage.timestamp >= datetime.combine(start_date, datetime.min.time()))

    if end_date:
        query = query.filter(LLMTokenUsage.timestamp < datetime.combine(end_date + timedelta(days=1), datetime.min.time()))

    token_usages = query.order_by(LLMTokenUsage.timestamp.desc()).all()
    return token_usages

@router.get("/all/", response_model=List[LLMTokenUsageInfo])
def read_all_users_llm_token_usage(
    admin_user: User = Depends(get_current_user), # To ensure only admin can access
    db: Session = Depends(get_db),
    start_date: Optional[date] = Query(None, description="Filter by start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Filter by end date (YYYY-MM-DD)")
):
    """
    Retrieve LLM token usage for all users. Admin access required.
    """
    # Admin Check
    if admin_user.user_type != "Admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized. Admin access required.")

    query = db.query(LLMTokenUsage) # No user_id filter to get all users' data

    if start_date:
        query = query.filter(LLMTokenUsage.timestamp >= datetime.combine(start_date, datetime.min.time()))

    if end_date:
        query = query.filter(LLMTokenUsage.timestamp < datetime.combine(end_date + timedelta(days=1), datetime.min.time()))

    # Order results, e.g., by timestamp or by user_id then timestamp
    token_usages = query.order_by(LLMTokenUsage.timestamp.desc()).all()
    return token_usages

@router.post("/", response_model=LLMTokenUsageInfo, status_code=status.HTTP_201_CREATED)
def create_llm_token_usage(
    usage_data: LLMTokenUsageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new LLM token usage record for the current user.
    """
    db_usage = LLMTokenUsage(
        user_id=current_user.id,
        session_id=usage_data.session_id,
        action=usage_data.action,
        model_name=usage_data.model_name,
        input_tokens=usage_data.input_tokens,
        output_tokens=usage_data.output_tokens,
        total_tokens=usage_data.total_tokens
    )
    
    db.add(db_usage)
    db.commit()
    db.refresh(db_usage)
    
    return db_usage
