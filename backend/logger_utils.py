# backend/logger_utils.py
import logging
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

# Assuming models are accessible, adjust import if needed
# Need to handle potential circular imports if models import this utils
try:
    from backend import models
except ImportError:
    models = None # Or handle differently if models must be available

logger = logging.getLogger(__name__)

def log_activity(
    db: Session,
    user_id: Optional[int],
    action: str,
    details: Optional[str] = None,
    target_entity: Optional[str] = None,
    target_entity_id: Optional[int] = None,
):
    """
    Creates an entry in the audit_logs table.

    Args:
        db: The database session.
        user_id: The ID of the user performing the action (can be None for system actions).
        action: A short code identifying the action (e.g., 'USER_LOGIN').
        details: A human-readable description of the event.
        target_entity: The type of entity affected (e.g., 'Student', 'Lesson').
        target_entity_id: The ID of the specific entity affected.
    """
    if models is None:
        logger.error("Models could not be imported in logger_utils. Cannot log activity.")
        return

    try:
        log_entry = models.AuditLog(
            user_id=user_id,
            action=action,
            details=details,
            target_entity=target_entity,
            target_entity_id=target_entity_id
            # timestamp is handled by server_default
        )
        db.add(log_entry)
        db.commit()
        # db.refresh(log_entry) # Usually not needed unless you need the log ID immediately
        logger.debug(f"Activity logged: User={user_id}, Action={action}, Target={target_entity}:{target_entity_id}")
    except Exception as e:
        db.rollback() # Rollback the log commit if it fails
        # Log the error, but don't let logging failure break the main operation
        logger.error(
            f"Failed to log activity to DB: User={user_id}, Action={action}, "
            f"Target={target_entity}:{target_entity_id}. Error: {e}",
            exc_info=False # Avoid excessive traceback spam for logging errors
        )
