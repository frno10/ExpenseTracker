# Expense Tracker Deployment Script for Windows
param(
    [string]$Environment = "production"
)

Write-Host "🚀 Deploying Expense Tracker..." -ForegroundColor Green

# Check if required tools are installed
function Test-Requirements {
    Write-Host "📋 Checking requirements..." -ForegroundColor Yellow
    
    if (!(Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Host "❌ Docker is not installed" -ForegroundColor Red
        exit 1
    }
    
    if (!(Get-Command docker-compose -ErrorAction SilentlyContinue)) {
        Write-Host "❌ Docker Compose is not installed" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "✅ All requirements met" -ForegroundColor Green
}

# Create production environment file
function New-EnvironmentFile {
    Write-Host "📝 Creating production environment..." -ForegroundColor Yellow
    
    if (!(Test-Path ".env.production")) {
        Write-Host "Creating .env.production file..." -ForegroundColor Yellow
        
        $envContent = @"
# Production Environment Variables
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-production-anon-key
SECRET_KEY=your-secure-production-secret-key
DEBUG=false
"@
        
        $envContent | Out-File -FilePath ".env.production" -Encoding UTF8
        Write-Host "⚠️  Please update .env.production with your actual values" -ForegroundColor Yellow
        exit 1
    }
    
    Write-Host "✅ Environment file ready" -ForegroundColor Green
}

# Build and deploy
function Start-Deployment {
    Write-Host "🔨 Building and deploying..." -ForegroundColor Yellow
    
    # Load environment variables
    if (Test-Path ".env.production") {
        Get-Content ".env.production" | ForEach-Object {
            if ($_ -match "^([^=]+)=(.*)$") {
                [Environment]::SetEnvironmentVariable($matches[1], $matches[2], "Process")
            }
        }
    }
    
    # Build and start services
    docker-compose -f docker-compose.prod.yml build
    docker-compose -f docker-compose.prod.yml up -d
    
    Write-Host "✅ Deployment complete!" -ForegroundColor Green
    Write-Host ""
    Write-Host "🌐 Your application is now running:" -ForegroundColor Cyan
    Write-Host "   Frontend: http://localhost" -ForegroundColor White
    Write-Host "   Backend:  http://localhost:8000" -ForegroundColor White
    Write-Host "   API Docs: http://localhost:8000/docs" -ForegroundColor White
}

# Health check
function Test-Health {
    Write-Host "🏥 Performing health check..." -ForegroundColor Yellow
    
    Start-Sleep -Seconds 10  # Wait for services to start
    
    # Check backend
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 10
        if ($response.StatusCode -eq 200) {
            Write-Host "✅ Backend is healthy" -ForegroundColor Green
        }
    }
    catch {
        Write-Host "❌ Backend health check failed" -ForegroundColor Red
        docker-compose -f docker-compose.prod.yml logs backend
        exit 1
    }
    
    # Check frontend
    try {
        $response = Invoke-WebRequest -Uri "http://localhost/health" -UseBasicParsing -TimeoutSec 10
        if ($response.StatusCode -eq 200) {
            Write-Host "✅ Frontend is healthy" -ForegroundColor Green
        }
    }
    catch {
        Write-Host "❌ Frontend health check failed" -ForegroundColor Red
        docker-compose -f docker-compose.prod.yml logs frontend
        exit 1
    }
    
    Write-Host "🎉 All services are healthy!" -ForegroundColor Green
}

# Main deployment flow
function Main {
    Write-Host "🚀 Expense Tracker Deployment" -ForegroundColor Cyan
    Write-Host "==============================" -ForegroundColor Cyan
    
    Test-Requirements
    New-EnvironmentFile
    Start-Deployment
    Test-Health
    
    Write-Host ""
    Write-Host "🎉 Deployment successful!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "1. Update your DNS to point to this server" -ForegroundColor White
    Write-Host "2. Set up SSL certificates" -ForegroundColor White
    Write-Host "3. Configure monitoring" -ForegroundColor White
    Write-Host ""
    Write-Host "To stop the application:" -ForegroundColor Yellow
    Write-Host "  docker-compose -f docker-compose.prod.yml down" -ForegroundColor White
    Write-Host ""
    Write-Host "To view logs:" -ForegroundColor Yellow
    Write-Host "  docker-compose -f docker-compose.prod.yml logs -f" -ForegroundColor White
}

# Run main function
Main