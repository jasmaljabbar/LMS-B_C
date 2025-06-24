from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session
import shutil
from backend.database import get_db
from backend.models import Homework, User
from backend.schemas import HomeworkCreate, HomeworkOut
import os
from uuid import uuid4
from fastapi.responses import FileResponse
from backend.dependencies import get_current_user

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
    """Create a new homework assignment with file upload"""
    # Generate unique filename
    file_extension = os.path.splitext(file.filename)[-1]
    unique_filename = f"{uuid4().hex}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Create homework record
    homework = Homework(
        title=title,
        description=description,
        student_id=student_id,
        grade_id=grade_id,
        subject_id=subject_id,
        lesson_id=lesson_id,
        image_path=file_path,
        parent_id=current_user.id  # Set parent_id from current user
    )
    
    db.add(homework)
    db.commit()
    db.refresh(homework)

    return homework

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
    """Get homeworks by parent ID (only accessible by the parent or admin)"""
    # Authorization check
    if current_user.id != parent_id and current_user.user_type != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access these homeworks"
        )
    
    homeworks = db.query(Homework).filter(Homework.parent_id == parent_id).all()
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