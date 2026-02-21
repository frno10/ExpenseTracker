# Expense Tracker

A personal finance management system with authentication, expense tracking, bank statement import, analytics, and category management. Built with FastAPI and React.

## Current State

See [PROJECT_ASSESSMENT.md](PROJECT_ASSESSMENT.md) for a detailed analysis and remediation history.

### Working End-to-End
- User registration and login (Supabase Auth with proper JWT verification)
- Expense CRUD (create, read, update, delete)
- Category listing with expense summaries
- PDF statement upload, preview, and import (CSOB bank parser)
- Dashboard with stats and spending-by-category pie chart
- Analytics with trends (line chart), categories (pie/bar charts + table), and computed insights
- CSV export of expense data
- Security headers on all responses
- Health check / monitoring endpoint

### Reconnected Modular Routers
The following routers are included in `main.py` with graceful degradation (they activate when their SQLAlchemy database dependencies are available):
- Budget management
- Recurring expenses
- Advanced analytics
- Payment methods / accounts
- Notes and attachments
- Data export (multi-format)
- WebSocket real-time updates
- Security endpoints
- Monitoring

### Not Yet Implemented
- Redis caching (architecture only)
- Database migrations (Alembic configured but migrations gitignored)
- E2E tests
- Rate limiting / CSRF middleware activation
- Multi-currency support

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
cp .env.example .env  # Edit with your Supabase credentials
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local  # Edit with your API URL
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
│   │   ├── main.py           # Application entry point
│   │   ├── api/              # Modular API routers
│   │   ├── services/         # Business logic layer
│   │   ├── models/           # SQLAlchemy + Pydantic models
│   │   ├── parsers/          # Statement parsers (PDF, CSV, Excel, OFX, QIF)
│   │   └── core/             # Auth, config, security, exceptions
│   └── tests/                # Backend tests
├── frontend/                 # React + TypeScript + Tailwind + Recharts
├── cli/                      # Click-based CLI (standalone)
├── scripts/                  # Setup and deployment scripts
├── docs/                     # Documentation
├── .github/workflows/        # CI/CD pipeline
└── .kiro/specs/              # Kiro requirement specs
```

**Architecture:** `main.py` handles auth, expense CRUD, and statement import using Supabase REST API directly. Modular routers (`app/api/*`) use SQLAlchemy with async PostgreSQL. Both connect to the same Supabase PostgreSQL database.

## Technology Stack

- **Backend**: Python, FastAPI, Supabase Auth, Pydantic
- **Database**: PostgreSQL (via Supabase)
- **Frontend**: React 18, TypeScript, Tailwind CSS, Shadcn/ui, Recharts
- **Testing**: pytest (backend), Vitest (frontend, 8 tests)
- **CI/CD**: GitHub Actions (lint, test, build)

## API Endpoints

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
- `POST /api/statement-import/upload` - Upload statement file
- `POST /api/statement-import/preview/{id}` - Preview parsed transactions
- `POST /api/statement-import/analyze-duplicates/{id}` - Check for duplicates
- `POST /api/statement-import/confirm/{id}` - Confirm and import

### Monitoring
- `GET /health` - Health check

## Configuration

Copy `.env.example` to `.env` in the backend directory:

```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
SECRET_KEY=your_secret_key
DEBUG=true
```

## Documentation

- [PROJECT_ASSESSMENT.md](PROJECT_ASSESSMENT.md) - Project assessment and remediation history
- [DEVELOPMENT.md](DEVELOPMENT.md) - Development setup guide
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) - Deployment guide
- [docs/FREE_DEPLOYMENT.md](docs/FREE_DEPLOYMENT.md) - Free tier deployment
- [docs/SUPABASE_AUTHENTICATION.md](docs/SUPABASE_AUTHENTICATION.md) - Auth system guide
- [docs/SECURITY.md](docs/SECURITY.md) - Security features status
- [docs/database/schema.md](docs/database/schema.md) - Database schema
- [API Docs](http://localhost:8000/docs) - Interactive API documentation (when running)

## License

This project is licensed under the MIT License.
