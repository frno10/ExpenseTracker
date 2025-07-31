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
1. Go to: https://supabase.com/dashboard/project/nsvdbcqvyphyiktrvtkw/sql
2. Copy all content from `backend/database_schema.sql`
3. Paste and click "Run"
4. Verify tables in: https://supabase.com/dashboard/project/nsvdbcqvyphyiktrvtkw/editor

### 3. Configure Environment Variables

The `.env` file should already be configured with your Supabase credentials:

```env
DATABASE_URL=postgresql+asyncpg://postgres:ExpenseTracker%2F56@db.nsvdbcqvyphyiktrvtkw.supabase.co:5432/postgres
SUPABASE_URL=https://nsvdbcqvyphyiktrvtkw.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5zdmRiY3F2eXBoeWlrdHJ2dGt3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTM4ODUzMjUsImV4cCI6MjA2OTQ2MTMyNX0.Mg8xh_x3mXwetx1NU3AocQpV5TovYpl1uxlEHlxFG-s
SECRET_KEY=dev-secret-key-change-in-production
DEBUG=true
```

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

## Frontend Setup (Optional)

If you want to run the frontend:

```powershell
# Navigate to frontend directory
cd ..\frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend will be available at http://localhost:3000

## Development Workflow

### Making Changes

1. **Backend Changes**: The server runs with `--reload` flag, so changes are automatically picked up
2. **Database Changes**: Currently using in-memory storage for development
3. **Environment Changes**: Restart the server after changing `.env` file

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
3. **Environment Variables**: Ensure `.env` file is in the `backend` directory

### Project Structure

```
backend/
├── app/
│   ├── main.py              # Single main application (THE ONLY ENTRY POINT)
│   ├── api/                 # API route modules (complex version - not used)
│   ├── core/                # Core utilities (complex version - not used)
│   ├── models/              # Data models (complex version - not used)
│   └── ...                  # Other modules (complex version - not used)
├── .env                     # Environment variables
├── requirements.txt         # Python dependencies
└── ...
```

**Important**: We use `app/main.py` as the single, complete application. The other modules in the `app/` directory are from a more complex version that had dependency issues.

## Supabase Integration

The application uses Supabase for:
- **Authentication**: User registration, login, JWT tokens
- **Database**: PostgreSQL database (though currently using in-memory storage for development)

### Supabase Dashboard

You can view your Supabase project at: https://supabase.com/dashboard/project/nsvdbcqvyphyiktrvtkw

## Next Steps

1. **Add Database Persistence**: Replace in-memory storage with actual Supabase database calls
2. **Add More Features**: Budgets, categories, file uploads, etc.
3. **Frontend Integration**: Connect the React frontend to this API
4. **Testing**: Add comprehensive test suite
5. **Deployment**: Deploy to production environment

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