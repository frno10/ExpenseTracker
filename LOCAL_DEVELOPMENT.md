# Local Development Setup

This guide helps you set up the ExpenseTracker application for local development with flexible environment switching between PostgreSQL and Supabase.

## 🚀 Quick Start

### Prerequisites
- Docker Desktop installed and running
- Python 3.11+ with virtual environment already set up (run `setup.ps1` or `setup.sh` first)

### Setup Local Development Environment

**Windows (PowerShell):**
```powershell
.\setup-local-dev.ps1
```

**Linux/macOS:**
```bash
./setup-local-dev.sh
```

This script will:
1. ✅ Check Docker installation and status
2. ⚙️ Copy `.env.local` to `.env` for local configuration
3. 🐘 Start PostgreSQL database in Docker
4. ⏳ Wait for database to be ready
5. 🔍 Test database connection
6. 📊 Display service information

## 🔄 Environment Switching (NEW!)

You can now easily switch between different development environments:

### Available Environments

| Environment | Database | Authentication | Use Case |
|-------------|----------|----------------|----------|
| **postgresql** | Local PostgreSQL | Local users | Full offline development |
| **supabase** | Remote Supabase | Supabase auth | Production-like testing |
| **hybrid** | Local PostgreSQL | Supabase auth | Best of both worlds |
| **production** | Remote Supabase | Supabase auth | Production deployment |

### Quick Switch Commands

**Windows (PowerShell):**
```powershell
# Full local development (recommended for daily work)
.\switch-env.ps1 postgresql

# Full Supabase (for testing with real auth)
.\switch-env.ps1 supabase

# Hybrid mode (local data + real auth)
.\switch-env.ps1 hybrid
```

**Linux/macOS:**
```bash
# Make executable first time
chmod +x switch-env.sh

# Then switch environments
./switch-env.sh postgresql
./switch-env.sh supabase
./switch-env.sh hybrid
```

> 📖 **For detailed environment switching documentation, see [ENVIRONMENT_SWITCHING.md](ENVIRONMENT_SWITCHING.md)**

## Manual Setup (Alternative)

If you prefer to set up manually:

### 1. Environment Configuration
```bash
# Copy local environment file
cp backend/.env.local backend/.env
```

### 2. Start PostgreSQL Database
```bash
cd backend
docker-compose -f docker-compose.dev.yml up -d postgres
```

### 3. Wait for Database
```bash
# Check if database is ready
docker-compose -f docker-compose.dev.yml exec postgres pg_isready -U expense_user -d expense_tracker
```

### 4. Start the Application
```bash
# Backend (from project root)
cd backend
python -m uvicorn app.main:app --reload

# Frontend (from project root, new terminal)
cd frontend
npm run dev
```

## Services Information

### PostgreSQL Database
- **Host:** localhost:5432
- **Database:** expense_tracker
- **Username:** expense_user
- **Password:** expense_pass
- **Connection String:** `postgresql+asyncpg://expense_user:expense_pass@localhost:5432/expense_tracker`

### Optional: pgAdmin (Database Management UI)
```bash
# Start pgAdmin
docker-compose -f backend/docker-compose.dev.yml --profile tools up -d pgadmin

# Access at: http://localhost:5050
# Email: admin@expense-tracker.local
# Password: admin123
```

## Environment Files

### `.env` (Production/Supabase)
- Uses Supabase REST API mode
- Points to remote Supabase database
- Used for production deployments

### `.env.local` (Local Development)
- Uses PostgreSQL mode
- Points to local Docker PostgreSQL
- Used for local development only
- **Not committed to git**

## Useful Commands

### Database Management
```bash
# Stop database
docker-compose -f backend/docker-compose.dev.yml down

# View database logs
docker-compose -f backend/docker-compose.dev.yml logs postgres

# Reset database (removes all data)
docker-compose -f backend/docker-compose.dev.yml down -v

# Connect to database directly
docker-compose -f backend/docker-compose.dev.yml exec postgres psql -U expense_user -d expense_tracker
```

### Application Development
```bash
# Start backend with auto-reload
cd backend && python -m uvicorn app.main:app --reload

# Start frontend with hot reload
cd frontend && npm run dev

# Run backend tests
cd backend && python -m pytest

# Check database connection
cd backend && python -c "from app.core.database import initialize_database; import asyncio; asyncio.run(initialize_database())"
```

## Troubleshooting

### Database Connection Issues
1. **Check Docker is running:** `docker info`
2. **Check container status:** `docker-compose -f backend/docker-compose.dev.yml ps`
3. **View logs:** `docker-compose -f backend/docker-compose.dev.yml logs postgres`
4. **Restart database:** `docker-compose -f backend/docker-compose.dev.yml restart postgres`

### Port Conflicts
If port 5432 is already in use:
1. Stop other PostgreSQL services
2. Or modify the port in `docker-compose.dev.yml` and update `DATABASE_URL` in `.env.local`

### Environment Issues
1. **Wrong environment:** Make sure `.env` contains local settings (copied from `.env.local`)
2. **Missing variables:** Check that all required variables are in `.env.local`

## Switching Between Environments

### Switch to Local Development
```bash
cp backend/.env.local backend/.env
# Start local database
docker-compose -f backend/docker-compose.dev.yml up -d postgres
```

### Switch to Supabase (Production)
```bash
cp backend/.env.production backend/.env  # or manually edit .env
# Stop local database if running
docker-compose -f backend/docker-compose.dev.yml down
```

## Database Schema

The application will automatically create all necessary tables when it starts up. The database initialization includes:
- User tables
- Expense tables
- Category tables
- Any other required schema

## 🎯 Recommended Development Workflow

### 1. Choose Your Environment
```powershell
# For daily development (fast, offline)
.\switch-env.ps1 postgresql

# For testing with real authentication
.\switch-env.ps1 hybrid

# For production-like testing
.\switch-env.ps1 supabase
```

### 2. Start Services
```bash
# If using PostgreSQL or Hybrid mode
docker-compose -f backend/docker-compose.dev.yml up -d postgres

# Start the backend
cd backend && python -m uvicorn app.main:app --reload

# Start the frontend (new terminal)
cd frontend && npm run dev
```

### 3. Access Your Application
- 📱 **Frontend:** http://localhost:3000
- 🔧 **API:** http://localhost:8000
- 📊 **Health Check:** http://localhost:8000/health
- 🗄️ **pgAdmin (optional):** http://localhost:5050

## 📚 Documentation Files

- **[ENVIRONMENT_SWITCHING.md](ENVIRONMENT_SWITCHING.md)** - Complete environment switching guide
- **[LOCAL_DEVELOPMENT.md](LOCAL_DEVELOPMENT.md)** - This file (setup guide)
- **[README.md](README.md)** - Main project documentation

## Next Steps

After setup is complete:
1. 🔄 **Choose environment:** Use `switch-env` script to select your preferred mode
2. 🚀 **Start backend:** `cd backend && python -m uvicorn app.main:app --reload`
3. 🌐 **Start frontend:** `cd frontend && npm run dev`
4. 📱 **Access app:** http://localhost:3000
5. 🔧 **Check API:** http://localhost:8000
6. 📊 **Monitor health:** http://localhost:8000/health