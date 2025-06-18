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

PDF_ENDPOINT = "/pdfs"

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
        db.query(models.PDF).delete()
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

# Sample data
@pytest.fixture
def sample_pdf_create(valid_lesson_id):
    return {"name": "Introduction to PDFs", "lesson_id": valid_lesson_id}

@pytest.fixture
def sample_pdf_update(valid_lesson_id):
    return {"name": "Updated PDF Name", "lesson_id": valid_lesson_id}

# Fixture to create a pdf and return its ID
@pytest.fixture
def created_pdf_id(authenticated_client, valid_lesson_id):
    # Create a dummy PDF file
    pdf_file = BytesIO(b"This is a dummy PDF file content.")
    files = {"pdf_file": ("test.pdf", pdf_file, "application/pdf")}  # filename, file-like object, content type

    data = {"pdf_name": "Initial PDF", "lesson_id": valid_lesson_id} # Pass other data as form data

    response = requests.post(f"{BASE_URL}{PDF_ENDPOINT}", files=files, data=data, headers=authenticated_client)
    assert response.status_code == status.HTTP_201_CREATED
    pdf = response.json()
    return pdf["id"]

def test_create_pdf(authenticated_client, valid_lesson_id):
    # Create a dummy PDF file
    pdf_file = BytesIO(b"This is a dummy PDF file content.")
    files = {"pdf_file": ("test.pdf", pdf_file, "application/pdf")}  # filename, file-like object, content type

    data = {"pdf_name": "New PDF", "lesson_id": valid_lesson_id} # Pass other data as form data

    response = requests.post(f"{BASE_URL}{PDF_ENDPOINT}", files=files, data=data, headers=authenticated_client)
    assert response.status_code == status.HTTP_201_CREATED
    pdf = response.json()
    assert "id" in pdf
    assert pdf["name"] == "New PDF"
    assert pdf["lesson_id"] == valid_lesson_id
    assert "url_id" in pdf

def test_create_pdf_invalid_lesson_id(authenticated_client):
    # Create a dummy PDF file
    pdf_file = BytesIO(b"This is a dummy PDF file content.")
    files = {"pdf_file": ("test.pdf", pdf_file, "application/pdf")}  # filename, file-like object, content type

    data = {"pdf_name": "Invalid PDF", "lesson_id": 9999} # Pass other data as form data
    response = requests.post(f"{BASE_URL}{PDF_ENDPOINT}", files=files, data=data, headers=authenticated_client)
    assert response.status_code == status.HTTP_400_BAD_REQUEST or response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY #Check validation status code

def test_create_pdf_missing_name(authenticated_client, valid_lesson_id):
    # Create a dummy PDF file
    pdf_file = BytesIO(b"This is a dummy PDF file content.")
    files = {"pdf_file": ("test.pdf", pdf_file, "application/pdf")}  # filename, file-like object, content type

    data = {"lesson_id": valid_lesson_id} # Missing pdf_name
    response = requests.post(f"{BASE_URL}{PDF_ENDPOINT}", files=files, data=data, headers=authenticated_client)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

def test_read_pdf(authenticated_client, created_pdf_id):
    response = requests.get(f"{BASE_URL}{PDF_ENDPOINT}/{created_pdf_id}", headers=authenticated_client)
    assert response.status_code == status.HTTP_200_OK
    pdf = response.json()
    assert pdf["id"] == created_pdf_id
    assert "name" in pdf
    assert "lesson_id" in pdf
    assert "url_id" in pdf

def test_read_pdf_not_found(authenticated_client):
    response = requests.get(f"{BASE_URL}{PDF_ENDPOINT}/9999", headers=authenticated_client)
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_read_pdfs(authenticated_client, valid_lesson_id):
     # Create a dummy PDF file
    pdf_file = BytesIO(b"This is a dummy PDF file content.")
    files = {"pdf_file": ("test.pdf", pdf_file, "application/pdf")}  # filename, file-like object, content type

    data = {"pdf_name": "List PDF", "lesson_id": valid_lesson_id} # Pass other data as form data

    # Create a pdf first to ensure there's something to read
    requests.post(f"{BASE_URL}{PDF_ENDPOINT}", files=files, data=data, headers=authenticated_client)

    response = requests.get(f"{BASE_URL}{PDF_ENDPOINT}", headers=authenticated_client)
    assert response.status_code == status.HTTP_200_OK
    pdfs = response.json()
    assert isinstance(pdfs, list)
    assert len(pdfs) > 0

def test_update_pdf(authenticated_client, created_pdf_id, valid_lesson_id):
    # Create a dummy PDF file for the update
    pdf_file = BytesIO(b"This is an updated dummy PDF file content.")
    files = {"pdf_file": ("updated_test.pdf", pdf_file, "application/pdf")}  # filename, file-like object, content type

    data = {"pdf_name": "Updated PDF Name", "lesson_id": valid_lesson_id} # Pass other data as form data
    response = requests.put(f"{BASE_URL}{PDF_ENDPOINT}/{created_pdf_id}", files=files, data=data, headers=authenticated_client)

    assert response.status_code == status.HTTP_200_OK
    updated_pdf = response.json()
    assert updated_pdf["id"] == created_pdf_id
    assert updated_pdf["name"] == "Updated PDF Name"
    assert updated_pdf["lesson_id"] == valid_lesson_id
    assert "url_id" in updated_pdf

def test_update_pdf_invalid_lesson_id(authenticated_client, created_pdf_id):
    # Create a dummy PDF file
    pdf_file = BytesIO(b"This is a dummy PDF file content.")
    files = {"pdf_file": ("test.pdf", pdf_file, "application/pdf")}  # filename, file-like object, content type

    data = {"pdf_name": "Invalid Update", "lesson_id": 9999}
    response = requests.put(f"{BASE_URL}{PDF_ENDPOINT}/{created_pdf_id}", files=files, data=data, headers=authenticated_client)
    assert response.status_code == status.HTTP_400_BAD_REQUEST or response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY #Check validation status code

def test_delete_pdf(authenticated_client, created_pdf_id):
    response = requests.delete(f"{BASE_URL}{PDF_ENDPOINT}/{created_pdf_id}", headers=authenticated_client)
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Verify that the pdf is actually deleted
    response = requests.get(f"{BASE_URL}{PDF_ENDPOINT}/{created_pdf_id}", headers=authenticated_client)
    assert response.status_code == status.HTTP_404_NOT_FOUND

@pytest.mark.skip
@pytest.mark.parametrize("upload_new_file", [True, False])
def test_update_pdf_file_reuse(authenticated_client, created_pdf_id, valid_lesson_id, db, upload_new_file):
    """
    Tests that the update_pdf function reuses the existing URL record when no new file is uploaded
    and updates the URL when a new file is uploaded.
    """
    initial_pdf = db.query(models.PDF).filter(models.PDF.id == created_pdf_id).first()

    # Check if initial_pdf exists before proceeding
    assert initial_pdf is not None, f"PDF with id {created_pdf_id} not found"

    initial_url_id = initial_pdf.url_id

    # Prepare update data
    data = {"pdf_name": "Updated PDF Name", "lesson_id": valid_lesson_id}
    files = {}

    if upload_new_file:
        # Create a dummy PDF file for the update
        pdf_file = BytesIO(b"This is an updated dummy PDF file content.")
        files = {"pdf_file": ("updated_test.pdf", pdf_file, "application/pdf")}  # filename, file-like object, content type

    # Perform the update
    response = requests.put(
        f"{BASE_URL}{PDF_ENDPOINT}/{created_pdf_id}",
        files=files,
        data=data,
        headers=authenticated_client,
    )
    assert response.status_code == status.HTTP_200_OK
    updated_pdf = response.json()

    # Fetch the updated PDF from the database
    updated_pdf_db = db.query(models.PDF).filter(models.PDF.id == created_pdf_id).first()

    if upload_new_file:
        # When a new file is uploaded, the URL ID should remain the same (existing url should be updated)
        assert updated_pdf_db.url_id == initial_url_id

        # Get URL from database, and confirm that the content is updated.
        url_db = db.query(models.URL).filter(models.URL.id == initial_url_id).first()

        assert url_db is not None
        assert "updated_test.pdf" in url_db.url

    else:
        # When no new file is uploaded, the URL ID should remain the same.
        assert updated_pdf_db.url_id == initial_url_id
        