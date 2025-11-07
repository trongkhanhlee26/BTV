# AI Agent Instructions for BTV Examination System

## Project Overview
This is a Django-based examination management system designed for conducting and scoring competitive exams. Key components:

- **Authentication**: Email-based login system for judges (`views_auth.py`)
- **Core Models** (`models.py`):
  - `CuocThi` (Competition)
  - `VongThi` (Competition Round) 
  - `BaiThi` (Exam/Test)
  - `ThiSinh` (Candidate)
  - `GiamKhao` (Judge)
  - `PhieuChamDiem` (Score Sheet)

## Key Architectural Patterns

### 1. Scoring System Types
Three distinct scoring methods exist (`views_score.py`):
```python
def _score_type(bt) -> str:
    # POINTS: Standard point-based scoring
    # TEMPLATE: Section/item-based scoring template 
    # TIME: Time-based scoring
```

### 2. Authentication & Authorization
- Uses Django session-based auth with custom `@judge_required` decorator
- Two roles: `ADMIN` and `JUDGE` defined in `GiamKhao` model
- Session keys: `judge_pk` and `judge_email`

### 3. Database Architecture
- PostgreSQL database (configured in `settings.py`)
- Uses Django's ORM with `BigAutoField` as default primary key
- Automatic code generation for models (e.g., `CTxxx` for competitions)

## Development Workflow

### Local Setup
1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Environment variables needed:
- `DJANGO_SECRET_KEY`
- `DEBUG` (0/1)
- `POSTGRES_*` settings for database

### Key Files for Common Tasks

1. **Adding New Scoring Methods**:
- Extend `_score_type()` in `views_score.py`
- Update `BaiThi.PHUONG_THUC_CHOICES`

2. **Modifying Authentication**:
- `decorators.py` for auth requirements
- `views_auth.py` for login/logout logic

3. **Data Import/Export**:
- CSV/Excel import handlers in `views_admin.py`
- Required column definitions in `REQUIRED_COLUMNS`

## Integration Points

### Frontend Integration
- Uses Django templates with static files in `core/static/`
- AJAX endpoints for scoring:
  - `score_template_api` for template-based scoring
  - `score_view` for general scoring

### API Conventions
1. Responses use consistent structure:
```python
{
    "ok": bool,
    "message": str,
    # Additional data specific to endpoint
}
```

2. Error handling convention:
```python
try:
    # Logic
except Exception as e:
    return JsonResponse({
        "ok": False,
        "message": f"Server error: {e.__class__.__name__}: {e}"
    }, status=500)
```

## Common Pitfalls & Solutions

1. **Database Transactions**: Always use `transaction.atomic()` for multi-table operations:
```python
with transaction.atomic():
    # Multiple model operations
```

2. **Score Calculation**: Different scoring types require specific handling:
- Points: Direct numeric scoring
- Template: Section-based rubric scoring 
- Time: Duration-based scoring with rules

3. **Judge Assignments**: Check `GiamKhaoBaiThi` for judge-exam relationships before allowing scoring