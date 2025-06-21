# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# Import existing routers...
from backend.routes import auth, teachers, parents, students, administrators
from backend.routes import urls, grades, sections, student_years
from backend.routes import subject, lesson, pdfs, video, images
from backend.routes import assessments
from backend.routes import homeworks
from backend.routes import assignment_samples
from backend.routes import assignment_formats
from backend.routes import assignment_distributions
from backend.routes import student_assignments
from backend.routes import student_assessment_scores # <--- This was already present, ensure it's not duplicated
from backend.routes import llm_usage as llm_usage_router # New router import
from backend.routes import terms
from backend.routes import dashboard as student_dashboard
from backend.routes import admin_dashboard
from backend.routes import teacher_dashboard
from backend.routes import parent_dashboard
from backend.routes import timetable
# from backend.routes import gcp

from backend.database import engine
from backend import models
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    # Database Initialization
    logger.info("Checking database connection and models...")
    models.Base.metadata.create_all(bind=engine)
    logger.info("Database tables checked/created via create_all().")
except Exception as e:
    logger.error(f"Error during initial database check/create_all: {e}", exc_info=True)
    raise SystemExit(f"Database connection/table creation failed: {e}")

app = FastAPI(
    title="AI Enabled LMS Backend",
    version="0.1.0",
    description="Backend API for the AI Enabled Learning Management System"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Include HTTP Routers ---
logger.info("Including HTTP API routers...")
app.include_router(auth.router)
app.include_router(administrators.router)
app.include_router(teachers.router)
app.include_router(parents.router)
app.include_router(students.router)
app.include_router(grades.router)
app.include_router(sections.router)
app.include_router(terms.router)
app.include_router(subject.router)
app.include_router(lesson.router)
app.include_router(student_years.router)
app.include_router(urls.router)
app.include_router(pdfs.router)
app.include_router(video.router)
app.include_router(images.router)
app.include_router(assessments.router)
app.include_router(homeworks.router)
app.include_router(assignment_samples.router)
app.include_router(assignment_formats.router)
app.include_router(assignment_distributions.router)
app.include_router(student_assignments.router)
app.include_router(student_assessment_scores.router) # <--- This was already present, ensure it's not duplicated
app.include_router(llm_usage_router.router, prefix="/llm-usage") # New router included
app.include_router(student_dashboard.router)
app.include_router(admin_dashboard.router)
app.include_router(teacher_dashboard.router)
app.include_router(parent_dashboard.router)
app.include_router(timetable.router)
# app.include_router(gcp.router)
logger.info("HTTP API routers included.")


# --- Root Endpoint ---
@app.get("/", tags=["Root"])
async def root():
    return {"message": "Welcome to the AI enabled LMS API"}


# --- Uvicorn Runner ---
if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Uvicorn server...")
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8080,
        reload=True
    )

