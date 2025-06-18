# backend/routes/timetable.py
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from sqlalchemy.exc import IntegrityError

from backend import models, schemas
from backend.database import get_db
from backend.dependencies import get_current_user
from backend.logger_utils import log_activity

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/timetables", tags=["Timetables"])

# --- Helper: Verify Admin --- (Or implement role checks directly)
def _verify_admin(current_user: models.User):
    if current_user.user_type != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to administrators."
        )

# --- Helper: Fetch Related Entities for Response ---
def _populate_timetable_info(db_timetable: models.Timetable) -> schemas.TimetableInfo:
    """Populates the TimetableInfo schema including related names."""
    return schemas.TimetableInfo(
        id=db_timetable.id,
        day_of_week=db_timetable.day_of_week,
        start_time=db_timetable.start_time,
        end_time=db_timetable.end_time,
        section_id=db_timetable.section_id,
        subject_id=db_timetable.subject_id,
        teacher_id=db_timetable.teacher_id,
        section_name=db_timetable.section.name if db_timetable.section else None,
        subject_name=db_timetable.subject.name if db_timetable.subject else None,
        teacher_name=db_timetable.teacher.name if db_timetable.teacher else None,
    )

# --- API Endpoints ---

@router.post("/", response_model=schemas.TimetableInfo, status_code=status.HTTP_201_CREATED)
def create_timetable_entry(
    timetable_data: schemas.TimetableCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Creates a new timetable entry."""
    _verify_admin(current_user) # Only Admins can create

    # --- Validate Foreign Keys ---
    section = db.query(models.Section.id).filter(models.Section.id == timetable_data.section_id).first()
    if not section:
        raise HTTPException(status_code=400, detail=f"Section with ID {timetable_data.section_id} not found.")
    subject = db.query(models.Subject.id).filter(models.Subject.id == timetable_data.subject_id).first()
    if not subject:
        raise HTTPException(status_code=400, detail=f"Subject with ID {timetable_data.subject_id} not found.")
    if timetable_data.teacher_id:
        teacher = db.query(models.Teacher.id).filter(models.Teacher.id == timetable_data.teacher_id).first()
        if not teacher:
            raise HTTPException(status_code=400, detail=f"Teacher with ID {timetable_data.teacher_id} not found.")
    # --- End Validation ---

    db_timetable = models.Timetable(**timetable_data.dict())

    try:
        db.add(db_timetable)
        db.commit()
        db.refresh(db_timetable)

        # Eager load relationships needed for the response population
        db.refresh(db_timetable, attribute_names=['section', 'subject', 'teacher'])

        logger.info(f"User '{current_user.username}' created timetable entry ID {db_timetable.id} for Section {db_timetable.section_id}")
        log_activity(
            db=db, user_id=current_user.id, action='TIMETABLE_CREATED',
            details=f"User '{current_user.username}' created timetable entry ID {db_timetable.id} for Section {db_timetable.section_id}, Subject {db_timetable.subject_id} on day {db_timetable.day_of_week}.",
            target_entity='Timetable', target_entity_id=db_timetable.id
        )
        return _populate_timetable_info(db_timetable)

    except IntegrityError as e:
        db.rollback()
        logger.error(f"Integrity error creating timetable entry: {e}", exc_info=True)
        # Check for specific constraint violations (e.g., unique constraint on time/day/section)
        if "uq_timetable_day_start_section" in str(e.orig) or "uq_timetable_day_end_section" in str(e.orig):
             raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An overlapping timetable entry already exists for this section on day {timetable_data.day_of_week} at the specified time."
            )
        # Add checks for other constraints if necessary
        else:
            raise HTTPException(status_code=400, detail="Database constraint violation during timetable creation.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating timetable entry: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create timetable entry.")


@router.get("/{timetable_id}", response_model=schemas.TimetableInfo)
def read_timetable_entry(
    timetable_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Retrieves a specific timetable entry by ID."""
    # Allow any authenticated user to read specific entry? Or restrict?
    # Let's restrict to Admin for now for direct ID access.
    _verify_admin(current_user)

    db_timetable = db.query(models.Timetable).options(
        joinedload(models.Timetable.section),
        joinedload(models.Timetable.subject),
        joinedload(models.Timetable.teacher)
    ).filter(models.Timetable.id == timetable_id).first()

    if db_timetable is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timetable entry not found")

    return _populate_timetable_info(db_timetable)


@router.get("/section/{section_id}", response_model=List[schemas.TimetableInfo])
def read_timetable_by_section(
    section_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Retrieves the full timetable for a specific section."""
    # Allow any authenticated user to view a section's timetable
    section = db.query(models.Section.id).filter(models.Section.id == section_id).first()
    if not section:
        raise HTTPException(status_code=404, detail=f"Section with ID {section_id} not found.")

    timetable_entries = db.query(models.Timetable).options(
        joinedload(models.Timetable.section), # Still load section for consistency
        joinedload(models.Timetable.subject),
        joinedload(models.Timetable.teacher)
    ).filter(
        models.Timetable.section_id == section_id
    ).order_by(
        models.Timetable.day_of_week, models.Timetable.start_time
    ).all()

    return [_populate_timetable_info(entry) for entry in timetable_entries]


@router.get("/teacher/{teacher_id}", response_model=List[schemas.TimetableInfo])
def read_timetable_by_teacher(
    teacher_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Retrieves all timetable entries assigned to a specific teacher."""
    # Authorization: Allow the specific teacher or an Admin
    is_self = (current_user.user_type == "Teacher" and current_user.teacher and current_user.teacher.id == teacher_id)
    is_admin = (current_user.user_type == "Admin")
    if not (is_self or is_admin):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this teacher's timetable")

    teacher = db.query(models.Teacher.id).filter(models.Teacher.id == teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail=f"Teacher with ID {teacher_id} not found.")

    timetable_entries = db.query(models.Timetable).options(
        joinedload(models.Timetable.section),
        joinedload(models.Timetable.subject),
        joinedload(models.Timetable.teacher) # Still load teacher for consistency
    ).filter(
        models.Timetable.teacher_id == teacher_id
    ).order_by(
        models.Timetable.day_of_week, models.Timetable.start_time
    ).all()

    return [_populate_timetable_info(entry) for entry in timetable_entries]


@router.put("/{timetable_id}", response_model=schemas.TimetableInfo)
def update_timetable_entry(
    timetable_id: int,
    timetable_update_data: schemas.TimetableUpdate, # Use update schema
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Updates an existing timetable entry."""
    _verify_admin(current_user) # Only Admins can update

    db_timetable = db.query(models.Timetable).filter(models.Timetable.id == timetable_id).first()
    if db_timetable is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timetable entry not found")

    # Get update data, excluding unset fields
    update_data = timetable_update_data.dict(exclude_unset=True)

    # --- Validate Foreign Keys if they are being updated ---
    if 'section_id' in update_data:
        section = db.query(models.Section.id).filter(models.Section.id == update_data['section_id']).first()
        if not section:
            raise HTTPException(status_code=400, detail=f"Section with ID {update_data['section_id']} not found.")
    if 'subject_id' in update_data:
        subject = db.query(models.Subject.id).filter(models.Subject.id == update_data['subject_id']).first()
        if not subject:
            raise HTTPException(status_code=400, detail=f"Subject with ID {update_data['subject_id']} not found.")
    if 'teacher_id' in update_data:
        if update_data['teacher_id'] is not None: # Allow setting teacher_id to NULL
            teacher = db.query(models.Teacher.id).filter(models.Teacher.id == update_data['teacher_id']).first()
            if not teacher:
                raise HTTPException(status_code=400, detail=f"Teacher with ID {update_data['teacher_id']} not found.")
    # --- End Validation ---

    # Apply updates
    updated_fields = []
    for key, value in update_data.items():
        if getattr(db_timetable, key) != value:
            setattr(db_timetable, key, value)
            updated_fields.append(key)

    if not updated_fields:
        logger.info(f"No changes detected for timetable entry {timetable_id}.")
        # Refresh relations for response even if no fields changed
        db.refresh(db_timetable, attribute_names=['section', 'subject', 'teacher'])
        return _populate_timetable_info(db_timetable) # Return current data

    try:
        db.commit()
        db.refresh(db_timetable)
        # Eager load relationships needed for the response population
        db.refresh(db_timetable, attribute_names=['section', 'subject', 'teacher'])

        logger.info(f"User '{current_user.username}' updated timetable entry ID {timetable_id}. Fields: {', '.join(updated_fields)}")
        log_activity(
            db=db, user_id=current_user.id, action='TIMETABLE_UPDATED',
            details=f"User '{current_user.username}' updated timetable entry ID {timetable_id}. Fields changed: {', '.join(updated_fields)}.",
            target_entity='Timetable', target_entity_id=timetable_id
        )
        return _populate_timetable_info(db_timetable)

    except IntegrityError as e:
        db.rollback()
        logger.error(f"Integrity error updating timetable entry {timetable_id}: {e}", exc_info=True)
        if "uq_timetable_day_start_section" in str(e.orig) or "uq_timetable_day_end_section" in str(e.orig):
             raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An overlapping timetable entry already exists for this section on this day/time."
            )
        else:
             raise HTTPException(status_code=400, detail="Database constraint violation during timetable update.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating timetable entry {timetable_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update timetable entry.")


@router.delete("/{timetable_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_timetable_entry(
    timetable_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Deletes a timetable entry."""
    _verify_admin(current_user) # Only Admins can delete

    db_timetable = db.query(models.Timetable).filter(models.Timetable.id == timetable_id).first()
    if db_timetable is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timetable entry not found")

    # Store details for logging before deleting
    details_for_log = f"Section {db_timetable.section_id}, Subject {db_timetable.subject_id}, Day {db_timetable.day_of_week}, Time {db_timetable.start_time}-{db_timetable.end_time}"

    try:
        db.delete(db_timetable)
        db.commit()
        logger.info(f"User '{current_user.username}' deleted timetable entry ID {timetable_id}")
        log_activity(
            db=db, user_id=current_user.id, action='TIMETABLE_DELETED',
            details=f"User '{current_user.username}' deleted timetable entry ID {timetable_id} ({details_for_log}).",
            target_entity='Timetable', target_entity_id=timetable_id
        )
        return None # Return None for 204 No Content
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting timetable entry {timetable_id}: {e}", exc_info=True)
        # Catch potential FK issues if cascade isn't set correctly, although unlikely for Timetable
        raise HTTPException(status_code=500, detail="Failed to delete timetable entry.")
