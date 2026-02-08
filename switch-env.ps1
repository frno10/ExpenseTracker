# Environment Switcher for ExpenseTracker Local Development
# This script switches between different local development environments

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("postgresql", "supabase", "hybrid", "production")]
    [string]$Environment
)

Write-Host "🔄 Switching to $Environment environment..." -ForegroundColor Cyan

# Define environment file mappings
$envFiles = @{
    "postgresql" = "backend\.env.local.postgresql"
    "supabase" = "backend\.env.local.supabase" 
    "hybrid" = "backend\.env.local.hybrid"
    "production" = "backend\.env.production"
}

# Check if the source environment file exists
$sourceFile = $envFiles[$Environment]
if (-not (Test-Path $sourceFile)) {
    Write-Host "❌ Environment file not found: $sourceFile" -ForegroundColor Red
    Write-Host "Available environments:" -ForegroundColor Yellow
    foreach ($env in $envFiles.Keys) {
        $file = $envFiles[$env]
        $exists = Test-Path $file
        $status = if ($exists) { "✅" } else { "❌" }
        Write-Host "  $status $env -> $file" -ForegroundColor $(if ($exists) { "Green" } else { "Red" })
    }
    exit 1
}

# Backup current .env if it exists
if (Test-Path "backend\.env") {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    Copy-Item "backend\.env" "backend\.env.backup.$timestamp"
    Write-Host "📋 Backed up current .env to .env.backup.$timestamp" -ForegroundColor Gray
}

# Copy the selected environment file to .env
Copy-Item $sourceFile "backend\.env"
Write-Host "✅ Switched to $Environment environment" -ForegroundColor Green

# Display current configuration
Write-Host ""
Write-Host "📊 Current Environment Configuration:" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan

# Read and display key configuration values
$envContent = Get-Content "backend\.env"
$configLines = $envContent | Where-Object { $_ -match "^(DATABASE_MODE|AUTH_MODE|SUPABASE_URL|DATABASE_URL|ENVIRONMENT)=" }

foreach ($line in $configLines) {
    if ($line -match "^([^=]+)=(.*)$") {
        $key = $matches[1]
        $value = $matches[2]
        
        # Mask sensitive values
        if ($key -eq "SUPABASE_KEY" -or $key -eq "SECRET_KEY") {
            $value = if ($value) { "***configured***" } else { "not set" }
        } elseif ($key -eq "DATABASE_URL" -and $value -match "://([^:]+):([^@]+)@") {
            $value = $value -replace "://([^:]+):([^@]+)@", "://***:***@"
        }
        
        $color = switch ($key) {
            "DATABASE_MODE" { "Yellow" }
            "AUTH_MODE" { "Magenta" }
            "ENVIRONMENT" { "Blue" }
            default { "White" }
        }
        
        Write-Host "  $key = $value" -ForegroundColor $color
    }
}

Write-Host ""
Write-Host "🚀 Next Steps:" -ForegroundColor Cyan

switch ($Environment) {
    "postgresql" {
        Write-Host "  1. Ensure PostgreSQL is running: docker-compose -f backend/docker-compose.dev.yml up -d postgres" -ForegroundColor White
        Write-Host "  2. Start backend: cd backend && python -m uvicorn app.main:app --reload" -ForegroundColor White
        Write-Host "  3. Register users locally through the API" -ForegroundColor White
    }
    "supabase" {
        Write-Host "  1. Stop local PostgreSQL if running: docker-compose -f backend/docker-compose.dev.yml down" -ForegroundColor White
        Write-Host "  2. Start backend: cd backend && python -m uvicorn app.main:app --reload" -ForegroundColor White
        Write-Host "  3. Use existing Supabase users or register new ones" -ForegroundColor White
    }
    "hybrid" {
        Write-Host "  1. Ensure PostgreSQL is running: docker-compose -f backend/docker-compose.dev.yml up -d postgres" -ForegroundColor White
        Write-Host "  2. Start backend: cd backend && python -m uvicorn app.main:app --reload" -ForegroundColor White
        Write-Host "  3. Authenticate with Supabase, data stored locally" -ForegroundColor White
    }
    "production" {
        Write-Host "  1. This uses production Supabase configuration" -ForegroundColor Yellow
        Write-Host "  2. Make sure you want to use production data!" -ForegroundColor Red
    }
}

Write-Host ""