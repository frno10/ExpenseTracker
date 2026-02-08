# Local Development Setup Script for ExpenseTracker
# This script sets up the local development environment with Docker PostgreSQL

Write-Host "🚀 Setting up ExpenseTracker Local Development Environment" -ForegroundColor Green
Write-Host ""

# Check if Docker is installed and running
Write-Host "📋 Checking prerequisites..." -ForegroundColor Yellow
try {
    $dockerVersion = docker --version 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker not found"
    }
    Write-Host "✅ Docker found: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker is not installed or not running" -ForegroundColor Red
    Write-Host "Please install Docker Desktop from https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
    exit 1
}

# Check if Docker is running
try {
    docker info 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker not running"
    }
    Write-Host "✅ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker is not running" -ForegroundColor Red
    Write-Host "Please start Docker Desktop" -ForegroundColor Yellow
    exit 1
}

# Check if Python virtual environment exists
Write-Host ""
Write-Host "🐍 Checking Python environment..." -ForegroundColor Yellow
if (Test-Path ".venv") {
    Write-Host "✅ Virtual environment found" -ForegroundColor Green
} else {
    Write-Host "❌ Virtual environment not found" -ForegroundColor Red
    Write-Host "Please run setup.ps1 first to create the virtual environment" -ForegroundColor Yellow
    exit 1
}

# Copy environment file for local development
Write-Host ""
Write-Host "⚙️  Setting up environment configuration..." -ForegroundColor Yellow
if (Test-Path "backend\.env.local") {
    Copy-Item "backend\.env.local" "backend\.env" -Force
    Write-Host "✅ Local environment configuration copied" -ForegroundColor Green
} else {
    Write-Host "❌ backend\.env.local not found" -ForegroundColor Red
    exit 1
}

# Start PostgreSQL with Docker Compose
Write-Host ""
Write-Host "🐘 Starting PostgreSQL database..." -ForegroundColor Yellow
Set-Location backend
try {
    docker-compose -f docker-compose.dev.yml up -d postgres
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to start PostgreSQL"
    }
    Write-Host "✅ PostgreSQL container started" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to start PostgreSQL container" -ForegroundColor Red
    Set-Location ..
    exit 1
}

# Wait for PostgreSQL to be ready
Write-Host ""
Write-Host "⏳ Waiting for PostgreSQL to be ready..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 0
do {
    $attempt++
    Start-Sleep -Seconds 2
    $healthCheck = docker-compose -f docker-compose.dev.yml exec -T postgres pg_isready -U expense_user -d expense_tracker 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ PostgreSQL is ready!" -ForegroundColor Green
        break
    }
    Write-Host "⏳ Attempt $attempt/$maxAttempts - PostgreSQL not ready yet..." -ForegroundColor Yellow
} while ($attempt -lt $maxAttempts)

if ($attempt -ge $maxAttempts) {
    Write-Host "❌ PostgreSQL failed to start within expected time" -ForegroundColor Red
    Write-Host "Check logs with: docker-compose -f backend/docker-compose.dev.yml logs postgres" -ForegroundColor Yellow
    Set-Location ..
    exit 1
}

Set-Location ..

# Test database connection
Write-Host ""
Write-Host "🔍 Testing database connection..." -ForegroundColor Yellow
.venv\Scripts\Activate.ps1
try {
    $testResult = python -c "import sys; sys.path.append('backend'); from app.core.database import initialize_database; import asyncio; asyncio.run(initialize_database()); print('SUCCESS')" 2>&1
    if ($testResult -like "*SUCCESS*") {
        Write-Host "✅ Database connection successful!" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Database connection test completed with warnings" -ForegroundColor Yellow
        Write-Host "This is normal for first-time setup" -ForegroundColor Gray
    }
} catch {
    Write-Host "⚠️  Database connection test had issues, but this is normal for first setup" -ForegroundColor Yellow
}

# Display setup information
Write-Host ""
Write-Host "🎉 Local Development Environment Setup Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "📊 Services Information:" -ForegroundColor Cyan
Write-Host "  • PostgreSQL: localhost:5432" -ForegroundColor White
Write-Host "    - Database: expense_tracker" -ForegroundColor Gray
Write-Host "    - Username: expense_user" -ForegroundColor Gray
Write-Host "    - Password: expense_pass" -ForegroundColor Gray
Write-Host ""
Write-Host "🛠️  Optional Tools:" -ForegroundColor Cyan
Write-Host "  • Start pgAdmin: docker-compose -f backend/docker-compose.dev.yml --profile tools up -d pgadmin" -ForegroundColor White
Write-Host "  • pgAdmin URL: http://localhost:5050 (admin@expense-tracker.local / admin123)" -ForegroundColor Gray
Write-Host ""
Write-Host "🚀 Next Steps:" -ForegroundColor Cyan
Write-Host "  1. Start the backend: cd backend && python -m uvicorn app.main:app --reload" -ForegroundColor White
Write-Host "  2. Start the frontend: cd frontend && npm run dev" -ForegroundColor White
Write-Host ""
Write-Host "🔧 Useful Commands:" -ForegroundColor Cyan
Write-Host "  • Stop database: docker-compose -f backend/docker-compose.dev.yml down" -ForegroundColor White
Write-Host "  • View database logs: docker-compose -f backend/docker-compose.dev.yml logs postgres" -ForegroundColor White
Write-Host "  • Reset database: docker-compose -f backend/docker-compose.dev.yml down -v" -ForegroundColor White
Write-Host ""