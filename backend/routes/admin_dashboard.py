# backend/routes/admin_dashboard.py
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload, Query # Import Query for type hinting
from sqlalchemy import func, cast, Date, select # Import select
from typing import List, Optional
from datetime import datetime, timedelta

from backend import models, schemas
from backend.database import get_db
from backend.dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/dashboard/admin",
    tags=["Admin Dashboard"],
    dependencies=[Depends(get_current_user)] # Apply auth to all endpoints here
)

# --- Helper: Check if Admin ---
def _verify_admin(current_user: models.User):
    if current_user.user_type != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to administrators."
        )

# --- API Endpoints ---

@router.get("/stats", response_model=List[schemas.StatCardData])
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Provides counts for key entities for the admin dashboard stat cards."""
    _verify_admin(current_user)
    try:
        total_users = db.query(func.count(models.User.id)).scalar()
        active_students = db.query(func.count(models.User.id)).filter(
            models.User.user_type == "Student", models.User.is_active == True
        ).scalar()
        active_teachers = db.query(func.count(models.User.id)).filter(
            models.User.user_type == "Teacher", models.User.is_active == True
        ).scalar()
        total_subjects = db.query(func.count(models.Subject.id)).scalar() # Assuming Subject ~ Course
        stats = [
            schemas.StatCardData(title="Total Users", count=total_users or 0),
            schemas.StatCardData(title="Active Students", count=active_students or 0),
            schemas.StatCardData(title="Active Teachers", count=active_teachers or 0),
            schemas.StatCardData(title="Total Courses", count=total_subjects or 0), # Renamed from Subjects
        ]
        return stats
    except Exception as e:
        logger.error(f"Error fetching admin dashboard stats: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not fetch dashboard statistics.")

@router.get("/user-activity-trend", response_model=List[schemas.DailyActivityData])
def get_user_activity_trend(
    days: int = 7, # Allow specifying number of days
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Provides user registration counts for the last N days (default 7).
    """
    _verify_admin(current_user)
    if days <= 0:
        raise HTTPException(status_code=400, detail="Number of days must be positive.")

    today = datetime.utcnow().date()
    start_date = today - timedelta(days=days - 1)

    try:
        # Query user creations grouped by date
        user_creation_data = db.query(
            cast(models.User.created_at, Date).label("creation_date"),
            func.count(models.User.id).label("daily_count")
        ).filter(
            cast(models.User.created_at, Date) >= start_date,
            cast(models.User.created_at, Date) <= today
        ).group_by(
            cast(models.User.created_at, Date)
        ).order_by(
            cast(models.User.created_at, Date)
        ).all()

        # Create a dictionary for quick lookup
        activity_dict = {result.creation_date: result.daily_count for result in user_creation_data}

        # Build the response for the last N days, filling missing days with 0
        trend_data: List[schemas.DailyActivityData] = []
        for i in range(days):
            day_date = start_date + timedelta(days=i)
            # Format day based on need - e.g., 'Mon', 'Tue' or 'YYYY-MM-DD'
            # day_label = day_date.strftime('%a') # Abbreviated day name
            day_label = day_date.strftime('%Y-%m-%d') # Full date might be better for trends > 7 days
            count = activity_dict.get(day_date, 0) # Default to 0 if no activity
            trend_data.append(schemas.DailyActivityData(day=day_label, count=count))

        return trend_data
    except Exception as e:
        logger.error(f"Error fetching user activity trend: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not fetch user activity data.")


@router.get("/recent-activities", response_model=List[schemas.RecentActivityItem])
def get_recent_activities(
    limit: int = 5, # Default to 5 recent items
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Retrieves the most recent audit log entries, including the username
    of the user who performed the action (if available).
    """
    _verify_admin(current_user)
    if limit <= 0:
        limit = 5 # Enforce a default positive limit

    try:
        # Query AuditLog and outer join with User to get username
        # Outer join handles cases where user_id is NULL or the user was deleted
        query: Query = db.query(
            models.AuditLog.id,
            models.AuditLog.timestamp,
            models.AuditLog.action,
            models.AuditLog.details,
            models.AuditLog.user_id,
            models.User.username, # Get username from joined table
            models.AuditLog.target_entity,
            models.AuditLog.target_entity_id
        ).outerjoin(
            models.User, models.AuditLog.user_id == models.User.id # Join condition
        ).order_by(
            models.AuditLog.timestamp.desc() # Order by most recent first
        ).limit(limit) # Apply limit

        results = query.all()

        # Map results directly using the schema's from_orm if possible
        # Ensure the schema fields match the query columns/labels
        # Pydantic V2 automatically maps if names match. For Pydantic V1, manual mapping might be safer.
        recent_activities = [
            schemas.RecentActivityItem(
                id=row.id,
                timestamp=row.timestamp,
                action=row.action,
                details=row.details,
                user_id=row.user_id,
                username=row.username, # Include username (will be None if user deleted/not found)
                target_entity=row.target_entity,
                target_entity_id=row.target_entity_id
            ) for row in results
        ]
        return recent_activities

    except Exception as e:
        logger.error(f"Error fetching recent activities: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not fetch recent activities.")


@router.get("/recent-users", response_model=List[schemas.RecentUserItem])
def get_recent_users(
    limit: int = 5, # Default to 5 recent users
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Gets the most recently active (logged-in) users."""
    _verify_admin(current_user)
    if limit <= 0:
        limit = 5

    try:
        # Query users ordered by last_login descending, NULLs last
        recent_users_query = db.query(
            models.User.id,
            models.User.username,
            models.User.email,
            models.User.user_type.label("role"),
            models.User.is_active.label("status"),
            models.User.last_login,
            models.User.created_at
        # --- CORRECTED ORDER BY for MySQL/MariaDB ---
        ).order_by(
            models.User.last_login.is_(None),  # Order by IS NULL ASC (False first, True last)
            models.User.last_login.desc()     # Then order by the date descending
        ).limit(limit)
        # --- END CORRECTION ---

        recent_users = recent_users_query.all()

        # Map results to the Pydantic schema
        # from_orm should work if the query labels match the schema fields
        return [schemas.RecentUserItem.from_orm(user) for user in recent_users]

    except Exception as e:
        # Log the specific SQL error if it occurs again
        logger.error(f"Error fetching recent users: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not fetch recent users.")
