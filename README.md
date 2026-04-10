# Curriculum Translation System - API Documentation

## Overview

RESTful API for translating curriculum documents (PDF, DOC, DOCX, Excel) between languages. Built with FastAPI, Celery for async tasks, and PostgreSQL.

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+ (for local development)

### Running the API

```bash
# Start all services
docker-compose up -d

# API runs at
http://localhost:8000

# API Documentation (Swagger UI)
http://localhost:8000/docs

# ReDoc Documentation
http://localhost:8000/redoc

# Celery Flower (task monitoring)
http://localhost:5555
```

### Initial Users (pre-seeded)

| Email | Password | Role |
|-------|----------|------|
| admin@curriculum.edu | admin123 | admin |
| teacher@curriculum.edu | teacher123 | teacher |
| student@curriculum.edu | student123 | student |
| translator@curriculum.edu | translator123 | translator |

---

## Authentication

All endpoints (except `/auth/login`) require JWT authentication.

### Login
```bash
POST /auth/login
Content-Type: application/json

{
  "email": "admin@curriculum.edu",
  "password": "admin123"
}

# Response
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

### Using the Token
Include in headers:
```
Authorization: Bearer <access_token>
```

### Token Refresh
```bash
POST /auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJ..."
}
```

### Get Current User
```bash
GET /auth/me
Authorization: Bearer <access_token>
```

---

## File Upload (Admin Only)

### Upload Book (PDF, DOC, DOCX)
```bash
POST /admin/books/upload
Authorization: Bearer <access_token>
Content-Type: multipart/form-data

file: <file>
title: "Book Title"
subject: "Kiswahili"
grade_level: "Form 1"
```

**Response:**
```json
{
  "id": "uuid",
  "title": "Book Title",
  "status": "pending",
  "message": "Book uploaded. PDF extraction in progress."
}
```

### Upload Exam (Excel)
```bash
POST /admin/exams/import
Authorization: Bearer <access_token>
Content-Type: multipart/form-data

file: <excel_file>
title: "Exam Title"
```

**Response:**
```json
{
  "id": "uuid",
  "title": "Exam Title",
  "sheet_names": ["Sheet1", "Sheet2"],
  "total_sheets": 2
}
```

---

## Translation

### Trigger Translation (Admin/Student)

```bash
POST /student/translate
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "content_type": "book",
  "content_id": "3ae81a60-03be-4725-89c5-e4dbc7279d9d",
  "language_id": 1,
  "source_language_id": 21
}
```

Or using query params:
```bash
POST /student/translate?content_type=book&content_id=<book_id>&language_id=1&source_language_id=21
```

**Parameters:**
- `content_type`: "book" or "exam"
- `content_id`: UUID of the uploaded content
- `language_id`: Target language ID
- `source_language_id`: Source language ID

**Language IDs:**
| ID | Language | Code |
|----|----------|------|
| 1 | Kiswahili | sw |
| 2 | Hausa | ha |
| 21 | English | en |

**Response:**
```json
{
  "translation_id": "uuid",
  "status": "pending",
  "task_id": "celery_task_id"
}
```

### Admin Trigger Translation
```bash
POST /admin/translations/translate
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "content_type": "book",
  "content_id": "<book_id>",
  "language_id": 1,
  "source_language_id": 21
}
```

### Check Translation Status

```bash
GET /student/translate/status/{job_id}
Authorization: Bearer <access_token>
```

### Get Translation

```bash
GET /student/translate/{translation_id}
Authorization: Bearer <access_token>

# Response
{
  "id": "uuid",
  "content_type": "book",
  "content_id": "uuid",
  "language_id": 1,
  "source_language_id": 21,
  "translated_text": "...",
  "status": "done",
  "chunk_count": 51,
  "created_at": "2026-04-09T12:00:00"
}
```

### Download Translation as PDF

```bash
GET /student/translate/{translation_id}/download
Authorization: Bearer <access_token>

# Returns PDF file
```

---

## Admin Endpoints

### List Books
```bash
GET /admin/books/
Authorization: Bearer <admin_token>
```

### Delete Book
```bash
DELETE /admin/books/{book_id}
Authorization: Bearer <admin_token>
```

### List Languages
```bash
GET /admin/languages
Authorization: Bearer <admin_token>
```

### Add Language
```bash
POST /admin/languages
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "name": "French",
  "code": "fr",
  "native_name": "Français",
  "libretranslate_code": "fr"
}
```

### Translation Stats
```bash
GET /admin/translations/stats
Authorization: Bearer <admin_token>

# Response
{
  "translations": {
    "total": 10,
    "completed": 8,
    "pending": 1,
    "failed": 1
  },
  "jobs": {
    "total": 10
  }
}
```

---

## Deployment / Shipping to Another Machine

### Prerequisites
- Docker & Docker Compose installed on target machine

### Files Needed
Copy these from this project:
1. All source code files
2. `.env` file (contains database passwords, secret keys, etc.)

### Running on New Machine

```bash
# 1. Navigate to project folder
cd Translation_Backend

# 2. Ensure .env exists (if not, copy from .env.example)
cp .env.example .env
# Then edit .env with your desired secrets

# 3. Start all services
docker-compose up -d

# 4. Check status
docker-compose ps
```

### First Time Setup
On first run, the database will be created automatically. The seed data (languages, test users) is loaded when the container starts.

### Default Test Users
| Email | Password | Role |
|-------|----------|------|
| admin@curriculum.edu | admin123 | admin |
| teacher@curriculum.edu | teacher123 | teacher |
| student@curriculum.edu | student123 | student |
| translator@curriculum.edu | translator123 | translator |

### Data Persistence
All data is stored in Docker volumes:
- `pgdata` - PostgreSQL database
- `redisdata` - Redis cache
- `libretranslate_data` - Translation models
- `./storage` folder - Uploaded files

To include existing data when shipping:
```bash
# Export database
docker-compose exec -T db pg_dump -U curriculum_user curriculum_db > backup.sql

# Import on new machine
docker-compose exec -T db psql -U curriculum_user curriculum_db < backup.sql
```

### Stopping
```bash
docker-compose down
```

---

## Environment Variables

Create `.env` file:
```env
DATABASE_URL=postgresql://curriculum_user:password@db/curriculum_db
REDIS_URL=redis://:password@redis:6379/0
SECRET_KEY=your-secret-key
LIBRETRANSLATE_URL=http://libretranslate:5000
GOOGLE_CLOUD_API_KEY=your-google-api-key
STORAGE_ROOT=/app/storage
DB_PASSWORD=password
REDIS_PASSWORD=password
```

---

## Docker Services

| Service | Port | Description |
|---------|------|-------------|
| backend | 8000 | FastAPI application |
| celery_worker | - | Background task worker |
| celery_flower | 5555 | Task monitoring UI |
| libretranslate | 5000 | Local translation API |
| postgres | 5432 | Database |
| redis | 6379 | Cache & message broker |

---

## Integration Notes

1. **File Upload**: Use `multipart/form-data` for file uploads
2. **Translations are cached**: Once translated, same content+language combo returns cached result
3. **Translation is async**: Use `task_id` to poll status or webhook for completion
4. **PDF download**: Returns PDF file directly, not JSON
5. **All IDs are UUIDs**: Use string representation in API calls