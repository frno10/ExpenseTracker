# ExpenseTracker Development Guide

Complete guide for setting up and developing the ExpenseTracker application with flexible environment switching.

## 📋 Table of Contents

1. [Quick Start](#quick-start)
2. [Environment Modes](#environment-modes)
3. [Setup Instructions](#setup-instructions)
4. [Environment Switching](#environment-switching)
5. [Development Workflow](#development-workflow)
6. [Troubleshooting](#troubleshooting)
7. [Advanced Configuration](#advanced-configuration)

## 🚀 Quick Start

### Prerequisites
- **Docker Desktop** - For local PostgreSQL database
- **Python 3.11+** - Backend runtime
- **Node.js 18+** - Frontend runtime
- **Git** - Version control

### One-Command Setup
```powershell
# Windows
.\setup-local-dev.ps1

# Linux/macOS  
./setup-local-dev.sh
```

## 🔄 Environment Modes

The ExpenseTracker supports four different development environments:

### 🐘 PostgreSQL Mode (Recommended for Development)
```powershell
.\switch-env.ps1 postgresql
```
- **Database:** Local PostgreSQL (Docker)
- **Authentication:** Local user accounts
- **Benefits:** Fast, offline, full control
- **Use Case:** Daily development, feature work

### ☁️ Supabase Mode (Production-like)
```powershell
.\switch-env.ps1 supabase
```
- **Database:** Remote Supabase
- **Authentication:** Supabase Auth
- **Benefits:** Production-like, shared data
- **Use Case:** Integration testing, demos

### 🔄 Hybrid Mode (Best of Both)
```powershell
.\switch-env.ps1 hybrid
```
- **Database:** Local PostgreSQL (Docker)
- **Authentication:** Supabase Auth
- **Benefits:** Real auth + local data
- **Use Case:** Testing auth flows locally

### 🚀 Production Mode
```powershell
.\switch-env.ps1 production
```
- **Database:** Remote Supabase
- **Authentication:** Supabase Auth
- **Benefits:** Exact production setup
- **Use Case:** Final testing, deployment

## 🛠️ Setup Instructions

### 1. Initial Setup
```bash
# Clone repository
git clone <repository-url>
cd ExpenseTracker

# Setup Python environment (Windows)
.\setup.ps1

# Setup Python environment (Linux/macOS)
./setup.sh

# Setup local development environment
.\setup-local-dev.ps1  # Windows
./setup-local-dev.sh   # Linux/macOS
```

### 2. Choose Development Environment
```powershell
# Start with PostgreSQL mode (recommended)
.\switch-env.ps1 postgresql
```

### 3. Start Services
```bash
# Start PostgreSQL (if using postgresql or hybrid mode)
docker-compose -f backend/docker-compose.dev.yml up -d postgres

# Start backend
cd backend
python -m uvicorn app.main:app --reload

# Start frontend (new terminal)
cd frontend
npm run dev
```

## 🔄 Environment Switching

### Switch Commands
```powershell
# Windows PowerShell
.\switch-env.ps1 [postgresql|supabase|hybrid|production]

# Linux/macOS
./switch-env.sh [postgresql|supabase|hybrid|production]
```

### What Happens When You Switch
1. **Backup** current `.env` file
2. **Copy** selected environment configuration
3. **Display** current configuration
4. **Show** next steps for the environment

### Environment Files
- `.env.local.postgresql` - Full local development
- `.env.local.supabase` - Full Supabase
- `.env.local.hybrid` - Mixed mode
- `.env.production` - Production config

## 💻 Development Workflow

### Typical Development Day
```bash
# 1. Morning: Start with fast local development
.\switch-env.ps1 postgresql
docker-compose -f backend/docker-compose.dev.yml up -d postgres

# 2. Develop features locally
cd backend && python -m uvicorn app.main:app --reload

# 3. Test with real authentication
.\switch-env.ps1 hybrid
# (PostgreSQL still running, just restart backend)

# 4. Final integration test
.\switch-env.ps1 supabase
docker-compose -f backend/docker-compose.dev.yml down
# (Restart backend to use Supabase)
```

### Team Collaboration
- **Individual work:** Use `postgresql` mode
- **Shared testing:** Use `supabase` or `hybrid` mode
- **Code reviews:** Use `hybrid` mode for consistent auth
- **Demos:** Use `supabase` mode

## 🔧 Service Information

### Local Services (PostgreSQL/Hybrid Mode)
- **PostgreSQL:** `localhost:5432`
  - Database: `expense_tracker`
  - Username: `expense_user`
  - Password: `expense_pass`
- **pgAdmin:** `http://localhost:5050` (optional)
  - Email: `admin@expense-tracker.local`
  - Password: `admin123`

### Application Services
- **Backend API:** `http://localhost:8000`
- **Frontend:** `http://localhost:3000`
- **Health Check:** `http://localhost:8000/health`
- **API Docs:** `http://localhost:8000/docs`

### Remote Services (Supabase Mode)
- **Supabase URL:** `https://nsvdbcqvyphyiktrvtkw.supabase.co`
- **Database:** Remote PostgreSQL
- **Authentication:** Supabase Auth

## 🐛 Troubleshooting

### Environment Switching Issues
```bash
# Check current environment
cat backend/.env | grep -E "(DATABASE_MODE|AUTH_MODE)"

# List available environment files
ls backend/.env.local.*

# Restore from backup
cp backend/.env.backup.YYYYMMDD_HHMMSS backend/.env
```

### Database Connection Issues
```bash
# PostgreSQL mode - check Docker
docker-compose -f backend/docker-compose.dev.yml ps
docker-compose -f backend/docker-compose.dev.yml logs postgres

# Supabase mode - check internet and credentials
curl -I https://nsvdbcqvyphyiktrvtkw.supabase.co
```

### Authentication Issues
```bash
# Check authentication logs (look for 🔐 [AUTH] messages)
# Backend will show detailed auth flow

# PostgreSQL mode - register local user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'

# Supabase mode - use existing Supabase account
```

### Port Conflicts
```bash
# Check what's using ports
netstat -an | findstr :5432  # PostgreSQL
netstat -an | findstr :8000  # Backend
netstat -an | findstr :3000  # Frontend

# Change ports in docker-compose.dev.yml if needed
```

## ⚙️ Advanced Configuration

### Custom Environment Files
Create your own environment files:
```bash
# Copy existing environment
cp backend/.env.local.postgresql backend/.env.local.custom

# Edit as needed
# Use with: .\switch-env.ps1 custom
```

### Database Initialization
```bash
# Reinitialize PostgreSQL database
docker-compose -f backend/docker-compose.dev.yml down -v
docker-compose -f backend/docker-compose.dev.yml up -d postgres

# Manual database setup
python -c "
import asyncio
from backend.app.core.database import initialize_database, init_db
asyncio.run(initialize_database())
asyncio.run(init_db())
"
```

### Performance Optimization
```bash
# Use pgAdmin for database management
docker-compose -f backend/docker-compose.dev.yml --profile tools up -d pgadmin

# Monitor API performance
curl http://localhost:8000/health

# Check database health
curl http://localhost:8000/api/v1/monitoring/health
```

## 📚 Related Documentation

- **[LOCAL_DEVELOPMENT.md](LOCAL_DEVELOPMENT.md)** - Basic setup guide
- **[ENVIRONMENT_SWITCHING.md](ENVIRONMENT_SWITCHING.md)** - Detailed environment switching
- **[README.md](README.md)** - Project overview
- **Backend API Docs:** `http://localhost:8000/docs` (when running)

## 🎯 Best Practices

### Development
1. **Start with PostgreSQL mode** for daily development
2. **Use Hybrid mode** when testing authentication flows
3. **Switch to Supabase mode** for integration testing
4. **Keep environment files in sync** with team requirements

### Database Management
1. **Backup important data** before switching environments
2. **Use pgAdmin** for complex database operations
3. **Monitor health endpoints** for system status
4. **Reset local database** when schema changes

### Team Collaboration
1. **Document environment requirements** for features
2. **Use consistent environments** for testing
3. **Share environment configurations** when needed
4. **Test in multiple environments** before merging

## 🚀 Next Steps

1. **Choose your environment:** `.\switch-env.ps1 postgresql`
2. **Start development:** Follow the workflow above
3. **Read detailed docs:** Check `ENVIRONMENT_SWITCHING.md`
4. **Join the team:** Use shared environments for collaboration

Happy coding! 🎉