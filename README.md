# Expense Tracker

A personal finance management system with authentication, expense tracking, statement import, and category management. Built with FastAPI and React.

## Current State

This project has substantial code (~53,800 lines of Python, ~6,800 lines of TypeScript) but there is a gap between what exists as code and what is actually wired into the running application. See [PROJECT_ASSESSMENT.md](PROJECT_ASSESSMENT.md) for a full analysis.

### Working End-to-End
- User registration and login (Supabase Auth)
- Expense CRUD (create, read, update, delete)
- Category listing with expense summaries
- PDF statement upload and preview (CSOB bank parser)
- Statement import to expenses
- Dashboard page with stats
- Health check / monitoring endpoint

### Coded but Not Connected
The following features have full implementations (services, API routers, models, tests) in `backend/app/` but their routers are **not included** in `main.py`. A backup file (`main_complex_backup.py`) shows they were once connected:

- Budget management (service + API + frontend pages)
- Recurring expenses (service + API + frontend pages)
- Advanced analytics (service + API + frontend pages)
- Payment methods / accounts
- Notes and attachments
- Data export (CSV, PDF, Excel)
- WebSocket real-time updates
- Security middleware (CSRF, rate limiting, security headers)
- Audit logging
- CLI application (Click-based)

### Not Implemented
- Redis caching (architecture only, no Redis connection)
- OpenTelemetry (code exists but dependency is optional/not installed)
- Chart visualizations (Recharts installed, no charts rendered)
- CI/CD pipeline
- Database migrations (Alembic configured but migrations gitignored)
- Frontend tests (1 test file with 1 test)

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- A Supabase account and project

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

**API**: http://localhost:8000
**API Docs**: http://localhost:8000/docs
**Frontend**: http://localhost:5173

## Project Structure

```
ExpenseTracker/
├── backend/
│   ├── app/
│   │   ├── main.py              # Running application (auth + expenses + statement import)
│   │   ├── main_complex_backup.py  # Backup showing all routers connected
│   │   ├── api/                 # Modular API routers (NOT wired into main.py)
│   │   ├── services/            # Business logic layer (NOT wired into main.py)
│   │   ├── models/              # SQLAlchemy + Pydantic models
│   │   ├── repositories/        # Data access layer
│   │   ├── parsers/             # Statement parsers (PDF, CSV, Excel, OFX, QIF)
│   │   └── core/                # Security, encryption, telemetry, config
│   ├── tests/                   # ~512 test functions (test the disconnected modules)
│   └── cli/                     # Click-based CLI (standalone, not connected to API)
├── frontend/                    # React + TypeScript + Tailwind + Shadcn/ui
├── docs/                        # Documentation
└── .kiro/specs/                 # Kiro requirement specs and task plans
```

**Important architectural note:** `main.py` uses Supabase REST API directly for data access. The modular `app/api/*` + `app/services/*` layer uses SQLAlchemy with async PostgreSQL. These are two different data access patterns that need to be reconciled before the routers can be reconnected.

## Technology Stack

- **Backend**: Python, FastAPI, Supabase Auth, Pydantic
- **Database**: PostgreSQL (via Supabase)
- **Frontend**: React, TypeScript, Tailwind CSS, Shadcn/ui
- **Testing**: pytest (backend), Vitest (frontend - minimal)

## API Endpoints (Currently Active)

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login user
- `GET /api/v1/auth/me` - Get current user

### Expenses
- `POST /api/v1/expenses` - Create expense
- `GET /api/v1/expenses` - List expenses
- `GET /api/v1/expenses/{id}` - Get specific expense
- `PUT /api/v1/expenses/{id}` - Update expense
- `DELETE /api/v1/expenses/{id}` - Delete expense

### Categories & Summary
- `GET /api/v1/categories` - Category summaries
- `GET /api/v1/summary` - Expense overview

### Statement Import
- `POST /api/v1/statements/upload` - Upload statement file
- `POST /api/v1/statements/{id}/preview` - Preview parsed transactions
- `POST /api/v1/statements/{id}/analyze-duplicates` - Check for duplicates
- `POST /api/v1/statements/{id}/confirm` - Confirm and import

### Monitoring
- `GET /health` - Health check

## Configuration

The application uses environment variables. Copy `.env.example` to `.env` in the backend directory:

```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
SECRET_KEY=your_secret_key
DEBUG=true
```

## Known Issues

1. **venv/ and node_modules/ are committed to git** - These should be removed with `git rm -r --cached`
2. **JWT signature verification disabled** in `main.py:297` - Security vulnerability
3. **Sensitive data logged** - Password lengths, token previews, Supabase URLs
4. **Two parallel data access patterns** - main.py uses Supabase REST, modules use SQLAlchemy
5. **Backend tests test disconnected code** - Tests pass but exercise modules that aren't in the running app

## Documentation

- [PROJECT_ASSESSMENT.md](PROJECT_ASSESSMENT.md) - Honest assessment of project state
- [DEVELOPMENT.md](DEVELOPMENT.md) - Development setup guide
- [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md) - Extended guide with environment switching
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) - Deployment guide
- [docs/SUPABASE_AUTHENTICATION.md](docs/SUPABASE_AUTHENTICATION.md) - Auth system guide
- [API Docs](http://localhost:8000/docs) - Interactive API documentation (when running)

## License

This project is licensed under the MIT License.
