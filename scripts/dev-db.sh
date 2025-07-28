#!/bin/bash
# Development database management script for Unix/Linux/macOS

ACTION=$1

case $ACTION in
    start)
        echo "Starting PostgreSQL database..."
        docker-compose up -d postgres
        echo "Waiting for database to be ready..."
        sleep 5
        docker-compose exec postgres pg_isready -U expense_user -d expense_tracker
        if [ $? -eq 0 ]; then
            echo "Database is ready!"
            echo "Connection string: postgresql://expense_user:expense_pass@localhost:5432/expense_tracker"
        fi
        ;;
    stop)
        echo "Stopping PostgreSQL database..."
        docker-compose down
        ;;
    restart)
        echo "Restarting PostgreSQL database..."
        docker-compose restart postgres
        ;;
    logs)
        echo "Showing database logs..."
        docker-compose logs -f postgres
        ;;
    reset)
        echo "Resetting database (this will delete all data)..."
        read -p "Are you sure? Type 'yes' to confirm: " confirm
        if [ "$confirm" = "yes" ]; then
            docker-compose down -v
            docker-compose up -d postgres
            echo "Database reset complete!"
        else
            echo "Reset cancelled."
        fi
        ;;
    *)
        echo "Usage: $0 [start|stop|restart|logs|reset]"
        exit 1
        ;;
esac