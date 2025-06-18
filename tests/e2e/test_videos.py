import pytest
import requests
from fastapi import status
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from io import BytesIO  # Import BytesIO

# Assuming your app is defined in backend.main
from backend.main import app
from backend import models

BASE_URL = "http://localhost:8000"  # Adjust if your app runs on a different port

VIDEO_ENDPOINT = "/videos"

# Database URL for testing - Retrieve from environment variable
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "mysql+pymysql://root:a@localhost/cloudnative_lms")

# Create a test database engine and session
engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables if they don't exist (optional, but recommended for clean tests)
models.Base.metadata.create_all(bind=engine)

# Utility function to get a token
def get_admin_token():
    login_data = {"username": "admin", "password": "Coimbatore"}  # Replace with actual admin credentials
    response = requests.post(f"{BASE_URL}/auth/login", data=login_data)
    assert response.status_code == status.HTTP_200_OK
    return response.json()["access_token"]

# Fixture for an authenticated client
@pytest.fixture
def authenticated_client():
    token = get_admin_token()
    headers = {"Authorization": f"Bearer {token}"}
    return headers  # Return the headers directly

# Fixture to get a database session for testing
@pytest.fixture
def db():
    db = TestingSessionLocal()
    try:
        # Clean up the tables before each test
        db.query(models.Video).delete()
        db.query(models.URL).delete()
        db.commit()
        yield db
    finally:
        db.close()

# Fixture to get a valid lesson ID from the database
@pytest.fixture
def valid_lesson_id(db):
    lesson = db.query(models.Lesson).first()
    if lesson:
        return lesson.id
    else:
        # If no lessons exist, create one for testing purposes
        subject = db.query(models.Subject).first()
        if not subject:
            grade = db.query(models.Grade).first()
            if not grade:
                new_grade = models.Grade(name="Test Grade")
                db.add(new_grade)
                db.commit()
                db.refresh(new_grade)
                grade_id = new_grade.id
            else:
                grade_id = grade.id

            new_subject = models.Subject(name="Test Subject", grade_id=grade_id)
            db.add(new_subject)
            db.commit()
            db.refresh(new_subject)
            subject_id = new_subject.id
        else:
            subject_id = subject.id

        new_lesson = models.Lesson(name="Test Lesson", subject_id=subject_id)
        db.add(new_lesson)
        db.commit()
        db.refresh(new_lesson)
        return new_lesson.id


# Fixture to create a video and return its ID
@pytest.fixture
def created_video_id(authenticated_client, valid_lesson_id, db):
    # Create a dummy video file
    video_file = BytesIO(b"This is a dummy video file content.")
    files = {"video_file": ("test.mp4", video_file, "video/mp4")}  # filename, file-like object, content type

    data = {"name": "Initial Video", "lesson_id": valid_lesson_id}  # Pass other data as form data

    response = requests.post(f"{BASE_URL}{VIDEO_ENDPOINT}", files=files, data=data, headers=authenticated_client)
    assert response.status_code == status.HTTP_201_CREATED
    video = response.json()
    return video["id"]


def test_create_video(authenticated_client, valid_lesson_id):
    # Create a dummy video file
    video_file = BytesIO(b"This is a dummy video file content.")
    files = {"video_file": ("test.mp4", video_file, "video/mp4")}  # filename, file-like object, content type

    data = {"name": "New Video", "lesson_id": valid_lesson_id}  # Pass other data as form data

    response = requests.post(f"{BASE_URL}{VIDEO_ENDPOINT}", files=files, data=data, headers=authenticated_client)
    assert response.status_code == status.HTTP_201_CREATED
    video = response.json()
    assert "id" in video
    assert video["name"] == "New Video"
    assert video["lesson_id"] == valid_lesson_id
    assert "url_id" in video


def test_create_video_invalid_lesson_id(authenticated_client):
    # Create a dummy video file
    video_file = BytesIO(b"This is a dummy video file content.")
    files = {"video_file": ("test.mp4", video_file, "video/mp4")}  # filename, file-like object, content type

    data = {"name": "Invalid Video", "lesson_id": 9999}  # Pass other data as form data
    response = requests.post(f"{BASE_URL}{VIDEO_ENDPOINT}", files=files, data=data, headers=authenticated_client)
    assert response.status_code == status.HTTP_400_BAD_REQUEST or response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY  # Check validation status code


def test_create_video_missing_name(authenticated_client, valid_lesson_id):
    # Create a dummy video file
    video_file = BytesIO(b"This is a dummy video file content.")
    files = {"video_file": ("test.mp4", video_file, "video/mp4")}  # filename, file-like object, content type

    data = {"lesson_id": valid_lesson_id}  # Missing name
    response = requests.post(f"{BASE_URL}{VIDEO_ENDPOINT}", files=files, data=data, headers=authenticated_client)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_read_video(authenticated_client, created_video_id, valid_lesson_id):
    response = requests.get(f"{BASE_URL}{VIDEO_ENDPOINT}/{created_video_id}", headers=authenticated_client)
    assert response.status_code == status.HTTP_200_OK
    video = response.json()
    assert video["id"] == created_video_id
    assert "name" in video
    assert "lesson_id" in video
    assert "url_id" in video


def test_read_video_not_found(authenticated_client):
    response = requests.get(f"{BASE_URL}{VIDEO_ENDPOINT}/9999", headers=authenticated_client)
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_read_videos(authenticated_client, valid_lesson_id):
    # Create a dummy video file
    video_file = BytesIO(b"This is a dummy video file content.")
    files = {"video_file": ("test.mp4", video_file, "video/mp4")}  # filename, file-like object, content type

    data = {"name": "List Video", "lesson_id": valid_lesson_id}  # Pass other data as form data

    # Create a video first to ensure there's something to read
    requests.post(f"{BASE_URL}{VIDEO_ENDPOINT}", files=files, data=data, headers=authenticated_client)

    response = requests.get(f"{BASE_URL}{VIDEO_ENDPOINT}", headers=authenticated_client)
    assert response.status_code == status.HTTP_200_OK
    videos = response.json()
    assert isinstance(videos, list)
    assert len(videos) > 0


def test_update_video(authenticated_client, created_video_id, valid_lesson_id):
    # Create a dummy video file for the update
    video_file = BytesIO(b"This is an updated dummy video file content.")
    files = {"video_file": ("updated_test.mp4", video_file, "video/mp4")}  # filename, file-like object, content type

    data = {"name": "Updated Video Name", "lesson_id": valid_lesson_id}  # Pass other data as form data
    response = requests.put(f"{BASE_URL}{VIDEO_ENDPOINT}/{created_video_id}", files=files, data=data, headers=authenticated_client)

    assert response.status_code == status.HTTP_200_OK
    updated_video = response.json()
    assert updated_video["id"] == created_video_id
    assert updated_video["name"] == "Updated Video Name"
    assert updated_video["lesson_id"] == valid_lesson_id
    assert "url_id" in updated_video


def test_update_video_invalid_lesson_id(authenticated_client, created_video_id):
    # Create a dummy video file
    video_file = BytesIO(b"This is a dummy video file content.")
    files = {"video_file": ("test.mp4", video_file, "video/mp4")}  # filename, file-like object, content type

    data = {"name": "Invalid Update", "lesson_id": 9999}  # Pass other data as form data
    response = requests.put(f"{BASE_URL}{VIDEO_ENDPOINT}/{created_video_id}", files=files, data=data, headers=authenticated_client)
    assert response.status_code == status.HTTP_400_BAD_REQUEST or response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY  # Check validation status code

@pytest.mark.skip
def test_delete_video(authenticated_client, created_video_id, db):
    # Get the video from the database to retrieve the URL ID
    video = db.query(models.Video).filter(models.Video.id == created_video_id).first()
    assert video is not None
    url_id = video.url_id

    # Delete the video
    response = requests.delete(f"{BASE_URL}{VIDEO_ENDPOINT}/{created_video_id}", headers=authenticated_client)
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Verify that the video is actually deleted
    response = requests.get(f"{BASE_URL}{VIDEO_ENDPOINT}/{created_video_id}", headers=authenticated_client)
    assert response.status_code == status.HTTP_404_NOT_FOUND

    # Verify that the URL is also deleted
    url = db.query(models.URL).filter(models.URL.id == url_id).first()
    assert url is None
    