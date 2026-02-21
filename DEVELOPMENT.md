# Development Setup Guide

This guide will help you set up and run the Expense Tracker application on your development machine.

## Prerequisites

- Python 3.8+ installed
- Node.js 16+ installed (for frontend)
- Git installed
- A Supabase account and project

## Quick Start (Windows)

### 1. Clone and Setup Backend

```powershell
# Navigate to the project
cd C:\Dev\ExpenseTracker

# Activate virtual environment
& .venv\Scripts\Activate.ps1

# Navigate to backend
cd backend

# Install dependencies (if not already done)
pip install -r requirements.txt
```

### 2. Set Up Database

**IMPORTANT**: Before the app will work, you need to create the database tables in Supabase.

```powershell
# Run the database setup helper
python setup_database.py
```

This will give you instructions to:
1. Open your Supabase SQL Editor
2. Run the SQL from `database_schema.sql` 
3. Verify tables were created

**Or manually**:
1. Go to your Supabase project SQL Editor
2. Copy all content from `backend/database_schema.sql`
3. Paste and click "Run"
4. Verify tables in the Table Editor

### 3. Configure Environment Variables

Copy `backend/.env.example` to `backend/.env` and fill in your Supabase credentials:

```env
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@db.YOUR_PROJECT.supabase.co:5432/postgres
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_KEY=your_supabase_anon_key
SECRET_KEY=generate-a-random-secret-key
DEBUG=true
```

For the frontend, create `frontend/.env.local` with your credentials:

```env
VITE_API_URL=http://localhost:8000/api/v1
VITE_SUPABASE_URL=https://YOUR_PROJECT.supabase.co
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
VITE_WS_URL=ws://localhost:8000/ws
VITE_NODE_ENV=development
```

**Note:** Never commit actual credentials to git. The `.env.local` file is ignored by git.

### 4. Start the Backend Server

```powershell
# From the backend directory with virtual environment activated
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at:
- **API Base**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### 5. Test the API

You can test the API using the interactive documentation at http://localhost:8000/docs or with curl:

```powershell
# Test health endpoint
curl http://localhost:8000/health

# Register a new user
curl -X POST "http://localhost:8000/api/v1/auth/register" `
  -H "Content-Type: application/json" `
  -d '{"email": "test@example.com", "password": "password123", "full_name": "Test User"}'

# Login
curl -X POST "http://localhost:8000/api/v1/auth/login" `
  -H "Content-Type: application/json" `
  -d '{"email": "test@example.com", "password": "password123"}'
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login user
- `GET /api/v1/auth/me` - Get current user info

### Expenses
- `POST /api/v1/expenses` - Create expense
- `GET /api/v1/expenses` - Get all expenses
- `GET /api/v1/expenses/{id}` - Get specific expense
- `PUT /api/v1/expenses/{id}` - Update expense
- `DELETE /api/v1/expenses/{id}` - Delete expense

### Categories & Summary
- `GET /api/v1/categories` - Get categories with summaries
- `GET /api/v1/summary` - Get expense summary

## Frontend Setup

To run the frontend for local development:

```powershell
# Navigate to frontend directory
cd ..\frontend

# Install dependencies (if not already done)
npm install

# Ensure you have .env.local file for local development
# (This should already exist with localhost:8000 API URL)

# Start development server
npm run dev
```

The frontend will be available at **http://localhost:5173** (Vite dev server)

**Environment Files:**
- `.env` - Production configuration (don't modify)
- `.env.local` - Local development configuration (points to localhost:8000)

## Development Workflow

### Making Changes

1. **Backend Changes**: The server runs with `--reload` flag, so changes are automatically picked up
2. **Database Changes**: Currently using in-memory storage for development
3. **Environment Changes**: Restart the server after changing `.env` file (backend) or `.env.local` file (frontend)

### Testing

```powershell
# Test the application loads
python -c "from app.main import app; print('✅ App loaded successfully')"

# Run with verbose logging
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level debug
```

### Common Issues

1. **Import Errors**: Make sure you're in the `backend` directory and virtual environment is activated
2. **Port Already in Use**: Kill existing processes or use a different port
3. **Environment Variables**: Ensure `.env` file is in the `backend` directory and `.env.local` is in the `frontend` directory

### Project Structure

```
backend/
├── app/
│   ├── main.py              # Running application (auth + expenses + statement import)
│   ├── main_complex_backup.py  # Backup showing all routers connected
│   ├── api/                 # Modular API routers (coded but NOT connected to main.py)
│   ├── services/            # Business logic layer (coded but NOT connected to main.py)
│   ├── models/              # SQLAlchemy + Pydantic models
│   ├── repositories/        # Data access layer
│   ├── parsers/             # Statement parsers (PDF, CSV, Excel, OFX, QIF)
│   └── core/                # Security, encryption, telemetry, config
├── tests/                   # ~512 test functions (test the disconnected modules)
├── cli/                     # Click-based CLI (standalone)
├── .env                     # Environment variables (not committed)
├── requirements.txt         # Python dependencies
└── ...
```

**Important**: `app/main.py` is the running entry point. It handles auth, expenses, and statement import using Supabase REST API directly. The modular `app/api/` + `app/services/` layer uses SQLAlchemy and is NOT connected to the running app. See [PROJECT_ASSESSMENT.md](PROJECT_ASSESSMENT.md) for details.

## Supabase Integration

The application uses Supabase for:
- **Authentication**: User registration, login, JWT tokens
- **Database**: PostgreSQL database (though currently using in-memory storage for development)

### Supabase Dashboard

You can view your Supabase project at: https://supabase.com/dashboard

## Known Issues & Next Steps

1. **Reconnect modular API routers** to main.py (budget, analytics, recurring expenses, etc.)
2. **Fix JWT signature verification** - currently disabled (`verify_signature: False`)
3. **Reconcile data access patterns** - main.py uses Supabase REST, modules use SQLAlchemy
4. **Remove venv/ and node_modules/ from git** - use `git rm -r --cached`
5. **Enable security middleware** - CSRF, rate limiting, security headers exist but aren't applied
6. **Add frontend tests** - only 1 test exists currently
7. **Set up CI/CD pipeline**

## Environment Configuration

### Frontend Environment Files

The frontend uses different environment files for different scenarios:

- **`.env`** - Production configuration (committed to git)
- **`.env.local`** - Local development configuration (ignored by git)

**For Local Development:**
```bash
cd frontend
npm run dev  # Uses .env.local (localhost:8000)
```

**For Production Build:**
```bash
cd frontend
npm run build  # Uses .env (production URLs)
```

**To Test Production Settings Locally:**
```bash
# Temporarily rename .env.local
mv .env.local .env.local.backup
npm run dev  # Now uses production .env
# Restore when done
mv .env.local.backup .env.local
```

## Troubleshooting

### Server Won't Start
```powershell
# Check if virtual environment is activated
# You should see (.venv) in your prompt

# Check if you're in the right directory
pwd  # Should be in backend directory

# Check if dependencies are installed
pip list | findstr fastapi
```

### Authentication Issues
- Verify Supabase credentials in `.env`
- Check Supabase project is active
- Ensure JWT secret key is correct

### API Not Responding
- Check if server is running on correct port
- Verify CORS settings allow your frontend domain
- Check firewall settings