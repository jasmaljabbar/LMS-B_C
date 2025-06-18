import pytest
import requests
from fastapi import status
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Assuming your app is defined in backend.main
from backend.main import app
from backend import models

BASE_URL = "http://localhost:8000"  # Adjust if your app runs on a different port

SUBJECT_ENDPOINT = "/subjects"

# Database URL for testing
TEST_DATABASE_URL = "mysql+pymysql://root:a@localhost/cloudnative_lms"  # Replace with your test DB

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
        yield db
    finally:
        db.close()

# Fixture to get a valid grade ID from the database
@pytest.fixture
def valid_grade_id(db):
    grade = db.query(models.Grade).first()
    if grade:
        return grade.id
    else:
        # If no grades exist, create one for testing purposes
        new_grade = models.Grade(name="Test Grade")
        db.add(new_grade)
        db.commit()
        db.refresh(new_grade)
        return new_grade.id

# Sample data
@pytest.fixture
def sample_subject_create(valid_grade_id):
    return {"name": "Science", "grade_id": valid_grade_id}

@pytest.fixture
def sample_subject_update(valid_grade_id):
    return {"name": "Updated Science", "grade_id": valid_grade_id}

# Fixture to create a subject and return its ID
@pytest.fixture
def created_subject_id(authenticated_client, sample_subject_create):
    response = requests.post(f"{BASE_URL}{SUBJECT_ENDPOINT}", json=sample_subject_create, headers=authenticated_client)
    assert response.status_code == status.HTTP_201_CREATED
    subject = response.json()
    return subject["id"]

def test_create_subject(authenticated_client, sample_subject_create):
    response = requests.post(f"{BASE_URL}{SUBJECT_ENDPOINT}", json=sample_subject_create, headers=authenticated_client)
    assert response.status_code == status.HTTP_201_CREATED
    subject = response.json()
    assert "id" in subject
    assert subject["name"] == sample_subject_create["name"]
    assert subject["grade_id"] == sample_subject_create["grade_id"]

@pytest.mark.skip
def test_create_subject_invalid_grade_id(authenticated_client):
    invalid_data = {"name": "Invalid Subject", "grade_id": 9999}
    response = requests.post(f"{BASE_URL}{SUBJECT_ENDPOINT}", json=invalid_data, headers=authenticated_client)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

def test_create_subject_missing_name(authenticated_client, valid_grade_id):
    invalid_data = {"grade_id": valid_grade_id}
    response = requests.post(f"{BASE_URL}{SUBJECT_ENDPOINT}", json=invalid_data, headers=authenticated_client)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

def test_read_subject(authenticated_client, created_subject_id, sample_subject_create):
    response = requests.get(f"{BASE_URL}{SUBJECT_ENDPOINT}/{created_subject_id}", headers=authenticated_client)
    assert response.status_code == status.HTTP_200_OK
    subject = response.json()
    assert subject["id"] == created_subject_id
    assert subject["name"] == sample_subject_create["name"]
    assert subject["grade_id"] == sample_subject_create["grade_id"]

def test_read_subject_not_found(authenticated_client):
    response = requests.get(f"{BASE_URL}{SUBJECT_ENDPOINT}/9999", headers=authenticated_client)
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_read_subjects(authenticated_client, sample_subject_create):
    # Create a subject first to ensure there's something to read
    requests.post(f"{BASE_URL}{SUBJECT_ENDPOINT}", json=sample_subject_create, headers=authenticated_client)

    response = requests.get(f"{BASE_URL}{SUBJECT_ENDPOINT}", headers=authenticated_client)
    assert response.status_code == status.HTTP_200_OK
    subjects = response.json()
    assert isinstance(subjects, list)
    assert len(subjects) > 0

def test_update_subject(authenticated_client, created_subject_id, sample_subject_create, sample_subject_update):
    response = requests.put(f"{BASE_URL}{SUBJECT_ENDPOINT}/{created_subject_id}", json=sample_subject_update, headers=authenticated_client)
    assert response.status_code == status.HTTP_200_OK
    updated_subject = response.json()
    assert updated_subject["id"] == created_subject_id
    assert updated_subject["name"] == sample_subject_update["name"]
    assert updated_subject["grade_id"] == sample_subject_update["grade_id"]

@pytest.mark.skip
def test_update_subject_invalid_grade_id(authenticated_client, created_subject_id):
    invalid_data = {"name": "Invalid Update", "grade_id": 9999}
    response = requests.put(f"{BASE_URL}{SUBJECT_ENDPOINT}/{created_subject_id}", json=invalid_data, headers=authenticated_client)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

def test_delete_subject(authenticated_client, created_subject_id):
    response = requests.delete(f"{BASE_URL}{SUBJECT_ENDPOINT}/{created_subject_id}", headers=authenticated_client)
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Verify that the subject is actually deleted
    response = requests.get(f"{BASE_URL}{SUBJECT_ENDPOINT}/{created_subject_id}", headers=authenticated_client)
    assert response.status_code == status.HTTP_404_NOT_FOUND