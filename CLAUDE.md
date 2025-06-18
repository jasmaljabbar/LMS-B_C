# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Local Development
```bash
# Quick start (recommended)
make start          # Creates venv, installs deps, starts server on port 8000
make stop           # Stops the server
make clean          # Cleans venv and stops server

# Manual setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### Database Operations
```bash
# Apply migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"

# Local MySQL setup (if needed)
mysql -u root -p
CREATE DATABASE cloudnative_lms;
GRANT ALL PRIVILEGES ON cloudnative_lms.* TO 'root'@'localhost' IDENTIFIED BY 'a';
```

### Testing
```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/test_ai.py                    # AI functionality tests
pytest tests/routes/                       # API endpoint tests
pytest tests/e2e/                         # End-to-end tests
```

### Cloud Deployment
```bash
cd terraform
terraform init
terraform apply

# Connect to Cloud SQL via proxy
cloud_sql_proxy ai-powered-lms:us-central1:cloudnative-lms-instance --credentials-file <path-to-credentials>
```

## High-Level Architecture

### Backend Structure (FastAPI)
- **Main Application**: `backend/main.py` - FastAPI app with all route inclusions
- **Database Models**: `backend/models.py` - SQLAlchemy models with complex relationships
- **Routes**: `backend/routes/` - Modular API endpoints by domain
- **AI Integration**: `backend/ai.py` - ChatManager class for Vertex AI interactions
- **Services**: `backend/services/` - Business logic layer

### User System Architecture
- **Multi-tenant Design**: Single `users` table with `user_type` field
- **Role-Specific Tables**: Separate `teachers`, `students`, `parents` tables linked via foreign keys
- **Parent-Student Relationship**: Many-to-many via `parent_student_association` table

### Content Hierarchy
```
Grades → Subjects → Lessons → Content (PDFs/Videos/Images)
```
- **URL Abstraction**: All files use `URL` model supporting GCS (`gs://`) and HTTPS URLs
- **File Storage**: Google Cloud Storage integration via `backend/routes/gcp.py`

### AI Integration Patterns
- **ChatManager**: Centralized AI interaction handling with session management
- **Token Tracking**: All AI operations logged in `llm_token_usage` table
- **Question Generation**: AI-powered assessment creation in `backend/services/question_generator.py`

### Assignment System
- **Template-Based**: `AssignmentFormat` → `AssignmentDistribution` → `StudentAssignment`
- **Flexible Distribution**: Assignments can target entire grades/subjects or specific students
- **Progress Tracking**: Student assessment scores linked to terms and subjects

## Key Database Models

### Core Entities
- `User`: Base user with type-specific relationships
- `Grade`, `Section`, `Subject`, `Lesson`: Educational hierarchy
- `Term`: Academic periods for organizing content
- `Assessment`, `AssignmentFormat`: Template and instance-based assignments

### Audit & Analytics
- `AuditLog`: User action tracking
- `LLMTokenUsage`: AI usage monitoring with cost tracking
- Relationships support comprehensive analytics queries

## Environment Configuration

### Required `.env` Variables (in `/backend/` directory)
```bash
DATABASE_URL=mysql+pymysql://user:password@host/database
SECRET_KEY=<generate with openssl rand -hex 32>
GOOGLE_APPLICATION_CREDENTIALS=<path-to-gcp-service-account-json>
```

### Default Admin Credentials
- Username: `admin`
- Password: `Coimbatore`
- Created via SQL insert with bcrypt hash

## Important Development Patterns

### Database Relationships
- Use cascade delete appropriately (`ondelete='CASCADE'`)
- Many-to-many relationships use association tables
- Audit logs use `SET NULL` to preserve logs when users are deleted

### AI Service Integration
- Always log token usage for AI operations
- Use `ChatManager.generate_answer()` for consistent AI interactions
- Sessions are managed per user for conversation continuity

### File Handling
- All file uploads go through GCP routes
- Use URL abstraction for flexible storage backends
- Support both cloud and local development patterns

### API Route Organization
- Group related endpoints in separate route files
- Use dependency injection for database sessions
- Consistent error handling and response patterns

## Testing Strategy
- **Unit Tests**: Focus on AI functionality and core business logic
- **Route Tests**: API endpoint validation
- **E2E Tests**: Full feature workflows (subjects, lessons, content management)
- Use pytest as the test runner

## Key Dependencies
- **FastAPI[all]**: Web framework with built-in validation and docs
- **SQLAlchemy + Alembic**: ORM and migrations
- **Vertex AI**: Google's AI platform integration
- **Google Cloud Storage**: File storage
- **Firebase Admin**: Authentication support
- **Python-JOSE**: JWT token handling