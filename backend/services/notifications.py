from sqlalchemy.orm import Session
from datetime import datetime
from backend.models import Homework, Student, User, Notification

async def send_completion_notification(
    homework: Homework,
    student: Student,
    parent: User,
    db: Session
):
    """
    Create a notification for the parent in the database
    """
    notification = Notification(
        user_id=parent.id,
        title=f"Homework Completed: {homework.title}",
        message=f"{student.name} has completed '{homework.title}'",
        related_entity_type="homework",
        related_entity_id=homework.id,
        created_at=datetime.utcnow()
    )
    
    db.add(notification)
    db.commit()
    return notification