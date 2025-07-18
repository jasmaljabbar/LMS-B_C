from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, logger, status
from sqlalchemy.orm import Session, joinedload  
import shutil
from backend.database import get_db
from backend.models import Homework, User, Student, Notification, StudentHomeworkScore
from backend.schemas import HomeworkCreate, HomeworkOut , NotificationOut, HomeworkScoreCreate
import os
from uuid import uuid4
from fastapi.responses import FileResponse
from backend.dependencies import get_current_user
from fastapi import BackgroundTasks
from backend.services.notifications import send_completion_notification
from fastapi import Response
import img2pdf


router = APIRouter(prefix="/homeworks", tags=["Homeworks"])

UPLOAD_DIR = "uploads/homeworks"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/", response_model=HomeworkOut, status_code=status.HTTP_201_CREATED)
async def create_homework(
    title: str,
    description: str = "",
    student_id: int = 0,
    grade_id: int = 0,
    subject_id: int = 0,
    lesson_id: int = 0,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new homework assignment with file upload (converted to PDF)"""
    try:
        # Create a temporary file to save the uploaded image
        temp_image_path = f"{uuid4().hex}{os.path.splitext(file.filename)[-1]}"
        with open(temp_image_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Convert the image to PDF using img2pdf
        pdf_bytes = img2pdf.convert(temp_image_path)

        # Generate unique filename for the PDF
        unique_filename = f"{uuid4().hex}.pdf"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)

        # Save the PDF to the UPLOAD_DIR
        with open(file_path, "wb") as pdf_file:
            pdf_file.write(pdf_bytes)

        # Create homework record
        homework = Homework(
            title=title,
            description=description,
            student_id=student_id,
            grade_id=grade_id,
            subject_id=subject_id,
            lesson_id=lesson_id,
            image_path=file_path,  # Save the path to the PDF
            parent_id=current_user.id
        )

        db.add(homework)
        db.commit()
        db.refresh(homework)

        return homework

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Clean up the temporary image file
        if os.path.exists(temp_image_path):
            os.remove(temp_image_path)

@router.get("/", response_model=List[HomeworkOut])
def get_all_homeworks(db: Session = Depends(get_db)):
    """Get all homeworks (admin only)"""
    return db.query(Homework).all()

@router.get("/image/{homework_id}")
def get_homework_image(homework_id: int, db: Session = Depends(get_db)):
    """Get homework image file by homework ID"""
    homework = db.query(Homework).filter(Homework.id == homework_id).first()
    if not homework:
        raise HTTPException(status_code=404, detail="Homework not found")
    
    image_path = homework.image_path
    if not os.path.isfile(image_path):
        raise HTTPException(status_code=404, detail="Image file not found")
    
    return FileResponse(path=image_path, media_type="image/jpeg", filename=os.path.basename(image_path))

@router.get("/by-student/{student_id}", response_model=List[HomeworkOut])
def get_homeworks_by_student(student_id: int, db: Session = Depends(get_db)):
    """Get homeworks by student ID"""
    homeworks = db.query(Homework).filter(Homework.student_id == student_id).all()
    return homeworks


@router.get("/by-parent/{parent_id}", response_model=List[HomeworkOut])
def get_homeworks_by_parent(
    parent_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get homeworks by parent ID (accessible by Parent or Admin)"""
    if current_user.id != parent_id and current_user.user_type not in ["Parent", "Admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access these homeworks"
        )

    homeworks = db.query(Homework)\
        .options(joinedload(Homework.subject))\
        .filter(Homework.parent_id == parent_id).all()

    return homeworks



@router.get("/by-parent-student/", response_model=List[HomeworkOut])
def get_homeworks_by_parent_and_student(
    parent_id: int,
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get homeworks by parent and student ID"""
    # Authorization check
    if current_user.id != parent_id and current_user.user_type != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access these homeworks"
        )
    
    homeworks = db.query(Homework).filter(
        Homework.parent_id == parent_id,
        Homework.student_id == student_id
    ).all()
    # Ensure grade_id is either an int or None
    for hw in homeworks:
        if hw.grade_id is None:
            hw.grade_id = None  # Explicitly set to None
    return homeworks

@router.get("/by-student-subject/", response_model=List[HomeworkOut])
def get_homeworks_by_student_and_subject(
    student_id: int,
    subject_id: int,
    db: Session = Depends(get_db)
):
    """Get homeworks by student and subject ID"""
    homeworks = db.query(Homework).filter(
        Homework.student_id == student_id,
        Homework.subject_id == subject_id
    ).all()
    return homeworks

def get_or_create_score_record(
    db: Session,
    student_id: int,
    homework_id: int,
    score_data: dict
) -> StudentHomeworkScore:
    """Handles automatic score recording"""
    score_record = db.query(StudentHomeworkScore).filter(
        StudentHomeworkScore.student_id == student_id,
        StudentHomeworkScore.homework_id == homework_id
    ).first()

    if score_record:
        # Update existing record
        score_record.score_achieved = score_data['score_achieved']
        score_record.max_score = score_data['max_score']
        score_record.comments = score_data['comments']
        score_record.graded_at = datetime.utcnow()
    else:
        # Create new auto-score record
        score_record = StudentHomeworkScore(
            student_id=student_id,
            homework_id=homework_id,
            score_achieved=score_data['score_achieved'],
            max_score=score_data['max_score'],
            comments=score_data['comments'],
            graded_by=None  # Auto-scored by system
        )
        db.add(score_record)
    
    return score_record


@router.patch("/{homework_id}/complete", response_model=HomeworkOut)
async def mark_homework_completed(
    homework_id: int,
    score_data: Optional[HomeworkScoreCreate] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    homework = db.query(Homework).options(
        joinedload(Homework.student),
        joinedload(Homework.parent)
    ).filter(Homework.id == homework_id).first()

    if not homework:
        raise HTTPException(status_code=404, detail="Homework not found")
    
    # Verify current user is the student assigned to this homework
    student = db.query(Student).filter(Student.user_id == current_user.id).first()
    if not student or student.id != homework.student_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the assigned student can mark homework as completed"
        )
    
    # Update homework status
    homework.completed = True
    homework.completed_at = datetime.utcnow()

    # Automatic scoring - always gives full points
    score_record = get_or_create_score_record(
        db=db,
        student_id=homework.student_id,
        homework_id=homework_id,
        score_data={
            'score_achieved': 1.0,  # Full points
            'max_score': 1.0,       # Using 1.0 scale (100%)
            'comments': "Automatically completed by student"
        }
    )

    db.commit()
    db.refresh(homework)
    
    # Get parent information
    parent = db.query(User).filter(User.id == homework.parent_id).first()
    
    # Create notification
    await send_completion_notification(
        homework=homework,
        student=student,
        parent=parent,
        db=db
    )
    
    return homework


@router.get("/notifications", response_model=List[NotificationOut])
async def get_user_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all notifications for the current user"""
    return db.query(Notification).filter(
        Notification.user_id == current_user.id
    ).order_by(Notification.created_at.desc()).all()

@router.patch("/notifications/{notification_id}/read", response_model=NotificationOut)
async def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark a notification as read"""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    notification.is_read = True
    db.commit()
    db.refresh(notification)
    
    return notification


@router.get("/student/completed", response_model=List[HomeworkOut])
def get_completed_homeworks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all completed homeworks for the current student"""
    # Assuming Student model has user_id that links to User
    student = db.query(Student).filter(Student.user_id == current_user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    return db.query(Homework).filter(
        Homework.student_id == student.id,
        Homework.completed == True
    ).all()

@router.get("/student/incomplete", response_model=List[HomeworkOut])
def get_incomplete_homeworks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all incomplete homeworks for the current student"""
    student = db.query(Student).filter(Student.user_id == current_user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    return db.query(Homework).filter(
        Homework.student_id == student.id,
        Homework.completed == False
    ).all()

@router.patch("/{homework_id}/incomplete", response_model=HomeworkOut)
def mark_homework_incomplete(
    homework_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark a completed homework as incomplete and remove its score"""
    # Get homework with related student
    homework = db.query(Homework).filter(Homework.id == homework_id).first()
    if not homework:
        raise HTTPException(status_code=404, detail="Homework not found")
    
    # Authorization - student or parent can mark incomplete
    student = db.query(Student).filter(Student.user_id == current_user.id).first()
    is_student = student and student.id == homework.student_id
    is_parent = current_user.id == homework.parent_id

    if not (is_student or is_parent):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only student or parent can mark homework incomplete"
        )
    
    # Update homework status
    homework.completed = False
    homework.completed_at = None
    
    # Remove associated score record if exists
    db.query(StudentHomeworkScore).filter(
        StudentHomeworkScore.homework_id == homework_id,
        StudentHomeworkScore.student_id == homework.student_id
    ).delete()
    
    db.commit()
    db.refresh(homework)
    
    return homework


@router.api_route("/pdfs/serve-homework/{homework_id}", methods=["GET", "HEAD"])
async def serve_homework_pdf(
    homework_id: int,
    db: Session = Depends(get_db)
):
    try:
        print(f"Requested homework PDF ID: {homework_id}")
        
        # 1. First get the homework record from database
        homework = db.query(Homework).filter(Homework.id == homework_id).first()
        if not homework:
            raise HTTPException(status_code=404, detail="Homework not found")
        
        # 2. Use the image_path from the homework record
        pdf_path = homework.image_path
        absolute_path = os.path.abspath(pdf_path)
        
        print(f"Looking for homework PDF at: {absolute_path}")
        
        if not os.path.exists(pdf_path):
            # List files in directory for debugging
            pdf_dir = os.path.dirname(pdf_path)
            if os.path.exists(pdf_dir):
                files = os.listdir(pdf_dir)
                print(f"Files in directory: {files}")
            raise HTTPException(
                status_code=404, 
                detail=f"Homework PDF not found at {absolute_path}"
            )
        
        return FileResponse(
            path=pdf_path,
            media_type="application/pdf",
            filename=f"homework_{homework_id}.pdf"  # You can customize the download filename
        )
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        print(f"Error serving homework PDF: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.delete("/{homework_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_homework(
    homework_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a homework assignment (accessible by Admin or Parent who created it)"""
    # Get the homework with relationships
    homework = db.query(Homework)\
        .filter(Homework.id == homework_id)\
        .first()
    
    if not homework:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Homework not found"
        )

    # Authorization check
    if current_user.user_type != "Admin" and current_user.user_type != "Parent":
        # print(current_user.id,homework.parent_id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins or the parent who created the homework can delete it"
        )

    try:
        # Delete the associated file if it exists
        if homework.image_path and os.path.exists(homework.image_path):
            try:
                os.remove(homework.image_path)
            except OSError as e:
                logger.error(f"Failed to delete homework file: {e}")

        # Delete the homework record
        db.delete(homework)
        db.commit()

    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting homework {homework_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete homework"
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)