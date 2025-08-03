#!/bin/bash

# Expense Tracker Deployment Script
set -e

echo "🚀 Deploying Expense Tracker..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if required tools are installed
check_requirements() {
    echo "📋 Checking requirements..."
    
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker is not installed${NC}"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}❌ Docker Compose is not installed${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ All requirements met${NC}"
}

# Create production environment file
create_env() {
    echo "📝 Creating production environment..."
    
    if [ ! -f .env.production ]; then
        echo "Creating .env.production file..."
        cat > .env.production << EOF
# Production Environment Variables
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-production-anon-key
SECRET_KEY=your-secure-production-secret-key
DEBUG=false
EOF
        echo -e "${YELLOW}⚠️  Please update .env.production with your actual values${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Environment file ready${NC}"
}

# Build and deploy
deploy() {
    echo "🔨 Building and deploying..."
    
    # Load environment variables
    export $(cat .env.production | xargs)
    
    # Build and start services
    docker-compose -f docker-compose.prod.yml build
    docker-compose -f docker-compose.prod.yml up -d
    
    echo -e "${GREEN}✅ Deployment complete!${NC}"
    echo ""
    echo "🌐 Your application is now running:"
    echo "   Frontend: http://localhost"
    echo "   Backend:  http://localhost:8000"
    echo "   API Docs: http://localhost:8000/docs"
}

# Health check
health_check() {
    echo "🏥 Performing health check..."
    
    sleep 10  # Wait for services to start
    
    # Check backend
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Backend is healthy${NC}"
    else
        echo -e "${RED}❌ Backend health check failed${NC}"
        docker-compose -f docker-compose.prod.yml logs backend
        exit 1
    fi
    
    # Check frontend
    if curl -f http://localhost/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Frontend is healthy${NC}"
    else
        echo -e "${RED}❌ Frontend health check failed${NC}"
        docker-compose -f docker-compose.prod.yml logs frontend
        exit 1
    fi
    
    echo -e "${GREEN}🎉 All services are healthy!${NC}"
}

# Main deployment flow
main() {
    echo "🚀 Expense Tracker Deployment"
    echo "=============================="
    
    check_requirements
    create_env
    deploy
    health_check
    
    echo ""
    echo -e "${GREEN}🎉 Deployment successful!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Update your DNS to point to this server"
    echo "2. Set up SSL certificates"
    echo "3. Configure monitoring"
    echo ""
    echo "To stop the application:"
    echo "  docker-compose -f docker-compose.prod.yml down"
    echo ""
    echo "To view logs:"
    echo "  docker-compose -f docker-compose.prod.yml logs -f"
}

# Run main function
main "$@"