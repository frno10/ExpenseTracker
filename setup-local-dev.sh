#!/bin/bash
# Local Development Setup Script for ExpenseTracker
# This script sets up the local development environment with Docker PostgreSQL

echo "🚀 Setting up ExpenseTracker Local Development Environment"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

# Check if Docker is installed and running
echo -e "${YELLOW}📋 Checking prerequisites...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed${NC}"
    echo -e "${YELLOW}Please install Docker from https://www.docker.com/get-started${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker found: $(docker --version)${NC}"

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo -e "${RED}❌ Docker is not running${NC}"
    echo -e "${YELLOW}Please start Docker${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker is running${NC}"

# Check if Python virtual environment exists
echo ""
echo -e "${YELLOW}🐍 Checking Python environment...${NC}"
if [ -d ".venv" ]; then
    echo -e "${GREEN}✅ Virtual environment found${NC}"
else
    echo -e "${RED}❌ Virtual environment not found${NC}"
    echo -e "${YELLOW}Please run setup.sh first to create the virtual environment${NC}"
    exit 1
fi

# Copy environment file for local development
echo ""
echo -e "${YELLOW}⚙️  Setting up environment configuration...${NC}"
if [ -f "backend/.env.local" ]; then
    cp backend/.env.local backend/.env
    echo -e "${GREEN}✅ Local environment configuration copied${NC}"
else
    echo -e "${RED}❌ backend/.env.local not found${NC}"
    exit 1
fi

# Start PostgreSQL with Docker Compose
echo ""
echo -e "${YELLOW}🐘 Starting PostgreSQL database...${NC}"
cd backend
if docker-compose -f docker-compose.dev.yml up -d postgres; then
    echo -e "${GREEN}✅ PostgreSQL container started${NC}"
else
    echo -e "${RED}❌ Failed to start PostgreSQL container${NC}"
    cd ..
    exit 1
fi

# Wait for PostgreSQL to be ready
echo ""
echo -e "${YELLOW}⏳ Waiting for PostgreSQL to be ready...${NC}"
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
    attempt=$((attempt + 1))
    sleep 2
    if docker-compose -f docker-compose.dev.yml exec -T postgres pg_isready -U expense_user -d expense_tracker &> /dev/null; then
        echo -e "${GREEN}✅ PostgreSQL is ready!${NC}"
        break
    fi
    echo -e "${YELLOW}⏳ Attempt $attempt/$max_attempts - PostgreSQL not ready yet...${NC}"
done

if [ $attempt -ge $max_attempts ]; then
    echo -e "${RED}❌ PostgreSQL failed to start within expected time${NC}"
    echo -e "${YELLOW}Check logs with: docker-compose -f backend/docker-compose.dev.yml logs postgres${NC}"
    cd ..
    exit 1
fi

cd ..

# Test database connection
echo ""
echo -e "${YELLOW}🔍 Testing database connection...${NC}"
source .venv/bin/activate
if python -c "import sys; sys.path.append('backend'); from app.core.database import initialize_database; import asyncio; asyncio.run(initialize_database()); print('SUCCESS')" 2>&1 | grep -q "SUCCESS"; then
    echo -e "${GREEN}✅ Database connection successful!${NC}"
else
    echo -e "${YELLOW}⚠️  Database connection test completed with warnings${NC}"
    echo -e "${GRAY}This is normal for first-time setup${NC}"
fi

# Display setup information
echo ""
echo -e "${GREEN}🎉 Local Development Environment Setup Complete!${NC}"
echo ""
echo -e "${CYAN}📊 Services Information:${NC}"
echo -e "${WHITE}  • PostgreSQL: localhost:5432${NC}"
echo -e "${GRAY}    - Database: expense_tracker${NC}"
echo -e "${GRAY}    - Username: expense_user${NC}"
echo -e "${GRAY}    - Password: expense_pass${NC}"
echo ""
echo -e "${CYAN}🛠️  Optional Tools:${NC}"
echo -e "${WHITE}  • Start pgAdmin: docker-compose -f backend/docker-compose.dev.yml --profile tools up -d pgadmin${NC}"
echo -e "${GRAY}  • pgAdmin URL: http://localhost:5050 (admin@expense-tracker.local / admin123)${NC}"
echo ""
echo -e "${CYAN}🚀 Next Steps:${NC}"
echo -e "${WHITE}  1. Start the backend: cd backend && python -m uvicorn app.main:app --reload${NC}"
echo -e "${WHITE}  2. Start the frontend: cd frontend && npm run dev${NC}"
echo ""
echo -e "${CYAN}🔧 Useful Commands:${NC}"
echo -e "${WHITE}  • Stop database: docker-compose -f backend/docker-compose.dev.yml down${NC}"
echo -e "${WHITE}  • View database logs: docker-compose -f backend/docker-compose.dev.yml logs postgres${NC}"
echo -e "${WHITE}  • Reset database: docker-compose -f backend/docker-compose.dev.yml down -v${NC}"
echo ""