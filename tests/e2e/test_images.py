import pytest
import requests
from fastapi import status
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from io import BytesIO

# Assuming your app is defined in backend.main
from backend.main import app
from backend import models

BASE_URL = "http://localhost:8000"  # Adjust if your app runs on a different port

IMAGE_ENDPOINT = "/images"

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
        # Clean up the tables before each test, in the CORRECT order!
        db.query(models.Image).delete()
        db.query(models.PDF).delete()  # Delete PDFs BEFORE URLs
        db.query(models.URL).delete()
        db.commit()
        yield db
    finally:
        db.close()
        
# Fixture to get a valid PDF ID from the database
@pytest.fixture
def valid_pdf_id(db):
    pdf = db.query(models.PDF).first()
    if pdf:
        return pdf.id
    else:
        # If no pdfs exist, create one for testing purposes
        lesson = db.query(models.Lesson).first()
        if not lesson:
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
            lesson_id = new_lesson.id
        else:
            lesson_id = lesson.id
        new_pdf = models.PDF(name="Test PDF", lesson_id=lesson_id)
        db.add(new_pdf)
        db.commit()
        db.refresh(new_pdf)
        return new_pdf.id

# Fixture to create an image and return its ID
@pytest.fixture
def created_image_id(authenticated_client, valid_pdf_id, db):
    # Create a dummy image file
    image_file = BytesIO(b"This is a dummy image file content.")
    files = {"image_file": ("test.jpg", image_file, "image/jpeg")}  # filename, file-like object, content type

    data = {
        "name": "Initial Image",
        "pdf_id": valid_pdf_id,
        "image_number": 1,
        "page_number": 1,
        "chapter_number": 1,
    }  # Pass other data as form data

    response = requests.post(
        f"{BASE_URL}{IMAGE_ENDPOINT}",
        files=files,
        data=data,
        headers=authenticated_client,
    )
    assert response.status_code == status.HTTP_201_CREATED
    image = response.json()
    return image["id"]


def test_create_image(authenticated_client, valid_pdf_id):
    # Create a dummy image file
    image_file = BytesIO(b"This is a dummy image file content.")
    files = {"image_file": ("test.jpg", image_file, "image/jpeg")}  # filename, file-like object, content type

    data = {
        "name": "New Image",
        "pdf_id": valid_pdf_id,
        "image_number": 1,
        "page_number": 1,
        "chapter_number": 1,
    }  # Pass other data as form data

    response = requests.post(
        f"{BASE_URL}{IMAGE_ENDPOINT}",
        files=files,
        data=data,
        headers=authenticated_client,
    )
    assert response.status_code == status.HTTP_201_CREATED
    image = response.json()
    assert "id" in image
    assert image["name"] == "New Image"
    assert image["pdf_id"] == valid_pdf_id
    assert "url_id" in image
    assert image["image_number"] == 1
    assert image["page_number"] == 1
    assert image["chapter_number"] == 1


def test_create_image_invalid_pdf_id(authenticated_client):
    # Create a dummy image file
    image_file = BytesIO(b"This is a dummy image file content.")
    files = {"image_file": ("test.jpg", image_file, "image/jpeg")}  # filename, file-like object, content type

    data = {
        "name": "Invalid Image",
        "pdf_id": 9999,
        "image_number": 1,
        "page_number": 1,
        "chapter_number": 1,
    }  # Pass other data as form data
    response = requests.post(
        f"{BASE_URL}{IMAGE_ENDPOINT}",
        files=files,
        data=data,
        headers=authenticated_client,
    )
    assert (
        response.status_code == status.HTTP_400_BAD_REQUEST
        or response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    )  # Check validation status code


def test_create_image_missing_name(authenticated_client, valid_pdf_id):
    # Create a dummy image file
    image_file = BytesIO(b"This is a dummy image file content.")
    files = {"image_file": ("test.jpg", image_file, "image/jpeg")}  # filename, file-like object, content type

    data = {
        "pdf_id": valid_pdf_id,
        "image_number": 1,
        "page_number": 1,
        "chapter_number": 1,
    }  # Missing name
    response = requests.post(
        f"{BASE_URL}{IMAGE_ENDPOINT}",
        files=files,
        data=data,
        headers=authenticated_client,
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_read_image(authenticated_client, created_image_id, valid_pdf_id):
    response = requests.get(
        f"{BASE_URL}{IMAGE_ENDPOINT}/{created_image_id}",
        headers=authenticated_client,
    )
    assert response.status_code == status.HTTP_200_OK
    image = response.json()
    assert image["id"] == created_image_id
    assert image["name"] == "Initial Image"
    assert image["pdf_id"] == valid_pdf_id
    assert "url_id" in image
    assert image["image_number"] == 1
    assert image["page_number"] == 1
    assert image["chapter_number"] == 1


def test_read_image_not_found(authenticated_client):
    response = requests.get(
        f"{BASE_URL}{IMAGE_ENDPOINT}/9999", headers=authenticated_client
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_read_images(authenticated_client, valid_pdf_id):
    # Create a dummy image file
    image_file = BytesIO(b"This is a dummy image file content.")
    files = {"image_file": ("test.jpg", image_file, "image/jpeg")}  # filename, file-like object, content type

    data = {
        "name": "List Image",
        "pdf_id": valid_pdf_id,
        "image_number": 1,
        "page_number": 1,
        "chapter_number": 1,
    }  # Pass other data as form data

    # Create a image first to ensure there's something to read
    requests.post(
        f"{BASE_URL}{IMAGE_ENDPOINT}",
        files=files,
        data=data,
        headers=authenticated_client,
    )

    response = requests.get(f"{BASE_URL}{IMAGE_ENDPOINT}", headers=authenticated_client)
    assert response.status_code == status.HTTP_200_OK
    images = response.json()
    assert isinstance(images, list)
    assert len(images) > 0


def test_update_image(authenticated_client, created_image_id, valid_pdf_id):
    # Create a dummy image file for the update
    image_file = BytesIO(b"This is an updated dummy image file content.")
    files = {"image_file": ("updated_test.jpg", image_file, "image/jpeg")}  # filename, file-like object, content type

    data = {
        "name": "Updated Image Name",
        "pdf_id": valid_pdf_id,
        "image_number": 2,
        "page_number": 2,
        "chapter_number": 2,
    }  # Pass other data as form data
    response = requests.put(
        f"{BASE_URL}{IMAGE_ENDPOINT}/{created_image_id}",
        files=files,
        data=data,
        headers=authenticated_client,
    )
    assert response.status_code == status.HTTP_200_OK
    updated_image = response.json()
    assert updated_image["id"] == created_image_id
    assert updated_image["name"] == "Updated Image Name"
    assert updated_image["pdf_id"] == valid_pdf_id
    assert "url_id" in updated_image
    assert updated_image["image_number"] == 2
    assert updated_image["page_number"] == 2
    assert updated_image["chapter_number"] == 2


def test_update_image_invalid_pdf_id(authenticated_client, created_image_id):
    # Create a dummy image file
    image_file = BytesIO(b"This is a dummy image file content.")
    files = {"image_file": ("test.jpg", image_file, "image/jpeg")}  # filename, file-like object, content type

    data = {
        "name": "Invalid Update",
        "pdf_id": 9999,
        "image_number": 2,
        "page_number": 2,
        "chapter_number": 2,
    }  # Pass other data as form data
    response = requests.put(
        f"{BASE_URL}{IMAGE_ENDPOINT}/{created_image_id}",
        files=files,
        data=data,
        headers=authenticated_client,
    )
    assert (
        response.status_code == status.HTTP_400_BAD_REQUEST
        or response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    )  # Check validation status code

@pytest.mark.skip
def test_delete_image(authenticated_client, created_image_id, db):
    # Get the image from the database to retrieve the URL ID

    image = db.query(models.Image).filter(models.Image.id == created_image_id).first()
    assert image is not None
    url_id = image.url_id
    # Delete the image
    response = requests.delete(
        f"{BASE_URL}{IMAGE_ENDPOINT}/{created_image_id}",
        headers=authenticated_client,
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Verify that the image is actually deleted
    response = requests.get(
        f"{BASE_URL}{IMAGE_ENDPOINT}/{created_image_id}",
        headers=authenticated_client,
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND

    # Verify that the URL is also deleted
    url = db.query(models.URL).filter(models.URL.id == url_id).first()
    assert url is None
