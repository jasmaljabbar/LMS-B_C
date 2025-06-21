# routers/homeworks.py

from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
import shutil
from backend.database import get_db
from backend.models import Homework
from backend.schemas import HomeworkCreate, HomeworkOut
import os
from uuid import uuid4
from fastapi.responses import FileResponse

router = APIRouter(prefix="/homeworks", tags=["Homeworks"])

UPLOAD_DIR = "uploads/homeworks"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/", response_model=HomeworkOut)
async def create_homework(
    title: str,
    description: str = "",
    student_id: int = 0,
    grade_id: int = 0,
    subject_id: int = 0,
    lesson_id: int = 0,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    file_extension = os.path.splitext(file.filename)[-1]
    unique_filename = f"{uuid4().hex}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    homework = Homework(
        title=title,
        description=description,
        student_id=student_id,
        grade_id=grade_id,
        subject_id=subject_id,
        lesson_id=lesson_id,
        image_path=file_path
    )
    db.add(homework)
    db.commit()
    db.refresh(homework)

    return homework


@router.get("/", response_model=List[HomeworkOut])
def get_all_homeworks(db: Session = Depends(get_db)):
    return db.query(Homework).all()



@router.get("/image/{homework_id}")
def get_homework_image(homework_id: int, db: Session = Depends(get_db)):
    homework = db.query(Homework).filter(Homework.id == homework_id).first()
    if not homework:
        raise HTTPException(status_code=404, detail="Homework not found")
    
    image_path = homework.image_path
    if not os.path.isfile(image_path):
        raise HTTPException(status_code=404, detail="Image file not found")
    
    return FileResponse(path=image_path, media_type="image/jpeg", filename=os.path.basename(image_path))

@router.get("/by-student/{student_id}", response_model=List[HomeworkOut])
def get_homeworks_by_student(student_id: int, db: Session = Depends(get_db)):
    homeworks = db.query(Homework).filter(Homework.student_id == student_id).all()
    return homeworks

@router.get("/by-student-subject/", response_model=List[HomeworkOut])
def get_homeworks_by_student_and_subject(
    student_id: int,
    subject_id: int,
    db: Session = Depends(get_db)
):
    homeworks = db.query(Homework).filter(
        Homework.student_id == student_id,
        Homework.subject_id == subject_id
    ).all()
    return homeworks

