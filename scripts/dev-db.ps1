# Development database management script for Windows

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("start", "stop", "restart", "logs", "reset")]
    [string]$Action
)

switch ($Action) {
    "start" {
        Write-Host "Starting PostgreSQL database..." -ForegroundColor Green
        docker-compose up -d postgres
        Write-Host "Waiting for database to be ready..." -ForegroundColor Yellow
        Start-Sleep -Seconds 5
        docker-compose exec postgres pg_isready -U expense_user -d expense_tracker
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Database is ready!" -ForegroundColor Green
            Write-Host "Connection string: postgresql://expense_user:expense_pass@localhost:5432/expense_tracker" -ForegroundColor Cyan
        }
    }
    "stop" {
        Write-Host "Stopping PostgreSQL database..." -ForegroundColor Yellow
        docker-compose down
    }
    "restart" {
        Write-Host "Restarting PostgreSQL database..." -ForegroundColor Yellow
        docker-compose restart postgres
    }
    "logs" {
        Write-Host "Showing database logs..." -ForegroundColor Cyan
        docker-compose logs -f postgres
    }
    "reset" {
        Write-Host "Resetting database (this will delete all data)..." -ForegroundColor Red
        $confirm = Read-Host "Are you sure? Type 'yes' to confirm"
        if ($confirm -eq "yes") {
            docker-compose down -v
            docker-compose up -d postgres
            Write-Host "Database reset complete!" -ForegroundColor Green
        } else {
            Write-Host "Reset cancelled." -ForegroundColor Yellow
        }
    }
}

Write-Host "`nUsage: .\scripts\dev-db.ps1 [start|stop|restart|logs|reset]" -ForegroundColor Gray