# Development Guide

This guide covers everything you need to know to develop and contribute to the Expense Tracker project.

## 🚀 Getting Started

### Prerequisites

Ensure you have the following installed:

- **Python 3.11+** - Backend development
- **Node.js 18+** - Frontend development  
- **Docker/Podman** - Database and services
- **Git** - Version control

### Development Environment Setup

#### 1. Clone and Setup Repository

```bash
git clone <repository-url>
cd expense-tracker
```

#### 2. Database Setup

Start the PostgreSQL database using Docker:

```bash
# Windows
.\scripts\dev-db.ps1 start

# Unix/Linux/macOS  
./scripts/dev-db.sh start
```

This will:
- Start PostgreSQL 15 in a container
- Create the `expense_tracker` database
- Set up user credentials (`expense_user:expense_pass`)
- Expose database on `localhost:5432`

#### 3. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate.ps1
# Unix/Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The backend will be available at `http://localhost:8000`

#### 4. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend will be available at `http://localhost:3000`

#### 5. CLI Setup

The CLI is available once the backend virtual environment is activated:

```bash
cd backend
source venv/bin/activate  # or venv\Scripts\activate.ps1

# Test CLI
python -m cli.main --help
python -m cli.main add --amount 25.50 --description "Test expense" --category food
```

## 🏗️ Project Structure

```
expense-tracker/
├── backend/                    # Python FastAPI backend
│   ├── app/                   # Main application code
│   │   ├── api/              # API route handlers
│   │   ├── core/             # Configuration and utilities
│   │   ├── models/           # Pydantic and SQLAlchemy models
│   │   ├── repositories/     # Data access layer
│   │   └── services/         # Business logic layer
│   ├── cli/                  # Command line interface
│   ├── tests/                # Backend tests
│   ├── alembic/              # Database migrations
│   ├── scripts/              # Utility scripts
│   └── requirements.txt      # Python dependencies
├── frontend/                  # React TypeScript frontend
│   ├── src/                  # Source code
│   │   ├── components/       # React components
│   │   ├── pages/           # Page components
│   │   ├── lib/             # Utilities and configurations
│   │   └── test/            # Frontend tests
│   └── package.json         # Node.js dependencies
├── docs/                     # Documentation
├── scripts/                  # Development scripts
└── .kiro/                    # Kiro specifications
```

## 🔧 Development Workflow

### Code Style and Formatting

#### Backend (Python)
```bash
cd backend

# Format code with Black
black .

# Type checking with mypy
mypy .

# Linting (configured in pyproject.toml)
# Runs automatically with pre-commit hooks
```

#### Frontend (TypeScript)
```bash
cd frontend

# Lint and fix
npm run lint

# Type checking
npm run build  # TypeScript compilation
```

### Pre-commit Hooks

Install pre-commit hooks to ensure code quality:

```bash
cd backend
pre-commit install
```

This will run the following on each commit:
- Black code formatting
- mypy type checking
- Basic file checks (trailing whitespace, etc.)

### Testing

#### Backend Tests
```bash
cd backend
source venv/bin/activate

# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_models.py

# Run with verbose output
pytest -v
```

#### Frontend Tests
```bash
cd frontend

# Run all tests
npm test

# Run tests in watch mode
npm run test:watch

# Run with coverage
npm run test:coverage
```

### Database Migrations

#### Creating Migrations
```bash
cd backend
source venv/bin/activate

# Auto-generate migration from model changes
alembic revision --autogenerate -m "Description of changes"

# Create empty migration for manual changes
alembic revision -m "Manual migration description"
```

#### Applying Migrations
```bash
# Apply all pending migrations
alembic upgrade head

# Apply specific migration
alembic upgrade <revision_id>

# Rollback one migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade <revision_id>
```

#### Migration Best Practices
- Always review auto-generated migrations before applying
- Test migrations on a copy of production data
- Include both upgrade and downgrade operations
- Use descriptive migration messages

## 🧪 Testing Strategy

### Test Structure

#### Backend Tests
```
tests/
├── conftest.py              # Pytest configuration and fixtures
├── test_models.py           # Model validation tests
├── test_repositories.py     # Repository layer tests
├── test_services.py         # Business logic tests
├── test_api/               # API endpoint tests
│   ├── test_expenses.py
│   ├── test_categories.py
│   └── test_auth.py
└── test_integration/       # Integration tests
    └── test_workflows.py
```

#### Frontend Tests
```
src/test/
├── setup.ts               # Test configuration
├── App.test.tsx           # Main app tests
├── components/            # Component tests
│   ├── Layout.test.tsx
│   └── Dashboard.test.tsx
└── utils/                 # Utility function tests
    └── api.test.ts
```

### Test Data Management

#### Backend Test Fixtures
```python
# conftest.py
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models import CategoryTable, PaymentMethodTable

@pytest.fixture
async def db_session():
    # Create test database session
    async with AsyncSessionLocal() as session:
        yield session

@pytest.fixture
async def sample_category(db_session: AsyncSession):
    category = CategoryTable(
        name="Test Category",
        color="#FF0000",
        is_custom=True
    )
    db_session.add(category)
    await db_session.commit()
    return category
```

#### Frontend Test Utilities
```typescript
// test/utils.tsx
import { render } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'

export function renderWithRouter(component: React.ReactElement) {
  return render(
    <BrowserRouter>
      {component}
    </BrowserRouter>
  )
}
```

## 🐛 Debugging

### Backend Debugging

#### Using Python Debugger
```python
# Add breakpoint in code
import pdb; pdb.set_trace()

# Or use modern debugger
import ipdb; ipdb.set_trace()
```

#### FastAPI Debug Mode
```python
# In app/main.py
app = FastAPI(debug=True)  # Enables detailed error pages
```

#### Database Query Debugging
```python
# Enable SQL logging
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

### Frontend Debugging

#### React Developer Tools
Install the React Developer Tools browser extension for component inspection.

#### Console Debugging
```typescript
// Add debug logs
console.log('Debug info:', data)
console.table(arrayData)  // Nice table format
console.group('API Call')
console.log('Request:', request)
console.log('Response:', response)
console.groupEnd()
```

#### Network Debugging
Use browser DevTools Network tab to inspect API calls and responses.

## 📊 Performance Monitoring

### Backend Performance

#### Database Query Analysis
```sql
-- Enable query logging in PostgreSQL
ALTER SYSTEM SET log_statement = 'all';
ALTER SYSTEM SET log_min_duration_statement = 100;  -- Log slow queries
SELECT pg_reload_conf();
```

#### API Performance Monitoring
```python
# Add timing middleware
import time
from fastapi import Request

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response
```

### Frontend Performance

#### Bundle Analysis
```bash
cd frontend

# Analyze bundle size
npm run build
npx vite-bundle-analyzer dist
```

#### Performance Profiling
Use React DevTools Profiler to identify performance bottlenecks.

## 🔧 Common Development Tasks

### Adding a New API Endpoint

1. **Define Pydantic Models** (if needed)
```python
# app/models/new_model.py
class NewModelCreate(CreateSchema):
    name: str
    description: Optional[str] = None
```

2. **Create Repository Methods**
```python
# app/repositories/new_repository.py
class NewRepository(BaseRepository):
    async def get_by_name(self, db: AsyncSession, name: str):
        # Implementation
        pass
```

3. **Add Service Layer**
```python
# app/services/new_service.py
class NewService:
    def __init__(self, repository: NewRepository):
        self.repository = repository
    
    async def create_item(self, data: NewModelCreate):
        # Business logic
        pass
```

4. **Create API Routes**
```python
# app/api/new_routes.py
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/api/new", tags=["new"])

@router.post("/", response_model=NewModelSchema)
async def create_item(data: NewModelCreate):
    # Route implementation
    pass
```

5. **Add Tests**
```python
# tests/test_api/test_new_routes.py
async def test_create_item(client: AsyncClient):
    response = await client.post("/api/new/", json={
        "name": "Test Item",
        "description": "Test Description"
    })
    assert response.status_code == 201
```

### Adding a New React Component

1. **Create Component**
```typescript
// src/components/NewComponent.tsx
interface NewComponentProps {
  title: string
  onAction: () => void
}

export function NewComponent({ title, onAction }: NewComponentProps) {
  return (
    <div className="p-4">
      <h2 className="text-xl font-bold">{title}</h2>
      <button onClick={onAction} className="btn btn-primary">
        Action
      </button>
    </div>
  )
}
```

2. **Add Tests**
```typescript
// src/components/NewComponent.test.tsx
import { render, screen, fireEvent } from '@testing-library/react'
import { NewComponent } from './NewComponent'

test('renders component with title', () => {
  const mockAction = jest.fn()
  render(<NewComponent title="Test Title" onAction={mockAction} />)
  
  expect(screen.getByText('Test Title')).toBeInTheDocument()
  
  fireEvent.click(screen.getByText('Action'))
  expect(mockAction).toHaveBeenCalled()
})
```

## 🚀 Deployment

### Development Deployment

#### Backend
```bash
cd backend
source venv/bin/activate

# Production-like server
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

#### Frontend
```bash
cd frontend

# Build for production
npm run build

# Preview production build
npm run preview
```

### Environment Variables

#### Backend (.env)
```bash
# Database
DATABASE_URL=postgresql+asyncpg://expense_user:expense_pass@localhost:5432/expense_tracker

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key

# Security
SECRET_KEY=your-super-secret-key-change-this-in-production
DEBUG=false
```

#### Frontend (.env)
```bash
# Supabase
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-supabase-anon-key

# API
VITE_API_URL=http://localhost:8000
```

## 🤝 Contributing Guidelines

### Git Workflow

1. **Create Feature Branch**
```bash
git checkout -b feature/new-feature-name
```

2. **Make Changes**
- Follow code style guidelines
- Add tests for new functionality
- Update documentation if needed

3. **Commit Changes**
```bash
git add .
git commit -m "feat: add new feature description"
```

Use conventional commit messages:
- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `test:` - Test additions/changes
- `refactor:` - Code refactoring

4. **Push and Create PR**
```bash
git push origin feature/new-feature-name
```

### Code Review Checklist

- [ ] Code follows style guidelines
- [ ] Tests are included and passing
- [ ] Documentation is updated
- [ ] No breaking changes (or properly documented)
- [ ] Performance impact considered
- [ ] Security implications reviewed

## 🆘 Troubleshooting

### Common Issues

#### Database Connection Issues
```bash
# Check if database is running
docker ps | grep postgres

# Check database logs
docker logs expense-tracker-db

# Reset database
.\scripts\dev-db.ps1 reset  # Windows
./scripts/dev-db.sh reset   # Unix
```

#### Python Import Issues
```bash
# Ensure virtual environment is activated
which python  # Should point to venv

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

#### Node.js Issues
```bash
# Clear npm cache
npm cache clean --force

# Delete node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

### Getting Help

- Check the [documentation](../README.md)
- Review [existing issues](link-to-issues)
- Ask questions in [discussions](link-to-discussions)
- Join the development chat (if available)

This development guide should help you get up and running quickly with the Expense Tracker project. Happy coding! 🚀