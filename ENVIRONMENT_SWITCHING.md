# Environment Switching Guide

This guide explains how to switch between different development environments for the ExpenseTracker application.

## Available Environments

### 🐘 PostgreSQL Mode (`postgresql`)

- **Database:** Local PostgreSQL (Docker)
- **Authentication:** Local (stored in PostgreSQL)
- **Use Case:** Full local development, offline work
- **File:** `.env.local.postgresql`


### ☁️ Supabase Mode (`supabase`)

- **Database:** Remote Supabase
- **Authentication:** Remote Supabase
- **Use Case:** Testing with production-like setup
- **File:** `.env.local.supabase`

### 🔄 Hybrid Mode (`hybrid`)

- **Database:** Local PostgreSQL (Docker)
- **Authentication:** Remote Supabase
- **Use Case:** Local data with real authentication
- **File:** `.env.local.hybrid`

### 🚀 Production Mode (`production`)

- **Database:** Remote Supabase
- **Authentication:** Remote Supabase
- **Use Case:** Production deployment
- **File:** `.env.production`

## Quick Switch Commands

### Windows (PowerShell)

```powershell
# Switch to PostgreSQL mode (full local)
.\switch-env.ps1 postgresql

# Switch to Supabase mode (full remote)
.\switch-env.ps1 supabase

# Switch to Hybrid mode (local DB + remote auth)
.\switch-env.ps1 hybrid

# Switch to Production mode
.\switch-env.ps1 production
```

### Linux/macOS

```bash
# Make script executable (first time only)
chmod +x switch-env.sh

# Switch to PostgreSQL mode (full local)
./switch-env.sh postgresql

# Switch to Supabase mode (full remote)
./switch-env.sh supabase

# Switch to Hybrid mode (local DB + remote auth)
./switch-env.sh hybrid

# Switch to Production mode
./switch-env.sh production
```

## Environment Details

### PostgreSQL Mode Setup

1. **Switch environment:** `.\switch-env.ps1 postgresql`
2. **Start PostgreSQL:** `docker-compose -f backend/docker-compose.dev.yml up -d postgres`
3. **Start backend:** `cd backend && python -m uvicorn app.main:app --reload`
4. **Register users:** Use `/api/v1/auth/register` endpoint

**Features:**

- ✅ Works offline
- ✅ Full control over data
- ✅ Fast local development
- ❌ Need to create users locally

### Supabase Mode Setup

1. **Switch environment:** `.\switch-env.ps1 supabase`
2. **Stop local DB:** `docker-compose -f backend/docker-compose.dev.yml down`
3. **Start backend:** `cd backend && python -m uvicorn app.main:app --reload`
4. **Use existing users:** Login with existing Supabase accounts

**Features:**

- ✅ Real authentication
- ✅ Shared data with team
- ✅ Production-like testing
- ❌ Requires internet connection

### Hybrid Mode Setup

1. **Switch environment:** `.\switch-env.ps1 hybrid`
2. **Start PostgreSQL:** `docker-compose -f backend/docker-compose.dev.yml up -d postgres`
3. **Start backend:** `cd backend && python -m uvicorn app.main:app --reload`
4. **Login with Supabase:** Use existing Supabase accounts

**Features:**

- ✅ Real authentication
- ✅ Local data storage
- ✅ Best of both worlds
- ⚠️ Users synced from Supabase to local DB

## Configuration Files

| Environment | File | Database | Auth | Use Case |
|-------------|------|----------|------|----------|
| PostgreSQL | `.env.local.postgresql` | Local PG | Local | Full local dev |
| Supabase | `.env.local.supabase` | Remote SB | Remote SB | Production-like |
| Hybrid | `.env.local.hybrid` | Local PG | Remote SB | Mixed mode |
| Production | `.env.production` | Remote SB | Remote SB | Deployment |

## Troubleshooting

### Environment Not Switching

- Check if the environment file exists
- Run the switch command from the project root
- Verify the `.env` file was updated

### Database Connection Issues

- **PostgreSQL mode:** Ensure Docker PostgreSQL is running
- **Supabase mode:** Check internet connection and Supabase status
- **Hybrid mode:** Ensure both PostgreSQL and internet are available

### Authentication Issues

- Check the logs for detailed authentication flow
- Verify Supabase credentials in the environment file
- For local auth, ensure users are registered in the local database

## Current Environment Check

To see which environment is currently active:

```bash
# Check current configuration
cat backend/.env | grep -E "(DATABASE_MODE|AUTH_MODE|SUPABASE_URL)"
```

## Backup and Recovery

The switch script automatically backs up your current `.env` file:

- Backups are saved as `.env.backup.YYYYMMDD_HHMMSS`
- To restore: `cp backend/.env.backup.YYYYMMDD_HHMMSS backend/.env`

## Development Workflow

### Typical Development Day

1. **Morning:** `.\switch-env.ps1 postgresql` (fast local development)
2. **Testing:** `.\switch-env.ps1 hybrid` (test with real auth)
3. **Integration:** `.\switch-env.ps1 supabase` (test full remote setup)

### Team Collaboration

- **Individual work:** Use `postgresql` mode
- **Shared testing:** Use `supabase` or `hybrid` mode
- **Demo/staging:** Use `production` mode

## Next Steps

After switching environments:

1. Restart your backend server
2. Clear browser cache/localStorage if needed
3. Re-authenticate if switching auth modes
4. Check the startup logs to confirm the configuration
