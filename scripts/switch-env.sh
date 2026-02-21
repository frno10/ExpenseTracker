#!/bin/bash
# Environment Switcher for ExpenseTracker Local Development
# This script switches between different local development environments

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
GRAY='\033[0;37m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Check if environment parameter is provided
if [ $# -eq 0 ]; then
    echo -e "${RED}❌ Please specify an environment${NC}"
    echo -e "${CYAN}Usage: ./switch-env.sh [postgresql|supabase|hybrid|production]${NC}"
    exit 1
fi

ENVIRONMENT=$1

echo -e "${CYAN}🔄 Switching to $ENVIRONMENT environment...${NC}"

# Define environment file mappings
declare -A ENV_FILES
ENV_FILES["postgresql"]="backend/.env.local.postgresql"
ENV_FILES["supabase"]="backend/.env.local.supabase"
ENV_FILES["hybrid"]="backend/.env.local.hybrid"
ENV_FILES["production"]="backend/.env.production"

# Check if the environment is valid
if [[ ! ${ENV_FILES[$ENVIRONMENT]+_} ]]; then
    echo -e "${RED}❌ Invalid environment: $ENVIRONMENT${NC}"
    echo -e "${YELLOW}Available environments: postgresql, supabase, hybrid, production${NC}"
    exit 1
fi

# Check if the source environment file exists
SOURCE_FILE=${ENV_FILES[$ENVIRONMENT]}
if [ ! -f "$SOURCE_FILE" ]; then
    echo -e "${RED}❌ Environment file not found: $SOURCE_FILE${NC}"
    echo -e "${YELLOW}Available environments:${NC}"
    for env in "${!ENV_FILES[@]}"; do
        file=${ENV_FILES[$env]}
        if [ -f "$file" ]; then
            echo -e "  ${GREEN}✅ $env -> $file${NC}"
        else
            echo -e "  ${RED}❌ $env -> $file${NC}"
        fi
    done
    exit 1
fi

# Backup current .env if it exists
if [ -f "backend/.env" ]; then
    timestamp=$(date +"%Y%m%d_%H%M%S")
    cp "backend/.env" "backend/.env.backup.$timestamp"
    echo -e "${GRAY}📋 Backed up current .env to .env.backup.$timestamp${NC}"
fi

# Copy the selected environment file to .env
cp "$SOURCE_FILE" "backend/.env"
echo -e "${GREEN}✅ Switched to $ENVIRONMENT environment${NC}"

# Display current configuration
echo ""
echo -e "${CYAN}📊 Current Environment Configuration:${NC}"
echo -e "${CYAN}=====================================${NC}"

# Read and display key configuration values
while IFS='=' read -r key value; do
    case $key in
        DATABASE_MODE)
            echo -e "  ${YELLOW}$key = $value${NC}"
            ;;
        AUTH_MODE)
            echo -e "  ${MAGENTA}$key = $value${NC}"
            ;;
        ENVIRONMENT)
            echo -e "  ${BLUE}$key = $value${NC}"
            ;;
        SUPABASE_KEY|SECRET_KEY)
            if [ -n "$value" ]; then
                echo -e "  ${WHITE}$key = ***configured***${NC}"
            else
                echo -e "  ${WHITE}$key = not set${NC}"
            fi
            ;;
        DATABASE_URL)
            # Mask password in DATABASE_URL
            masked_value=$(echo "$value" | sed 's|://[^:]*:[^@]*@|://***:***@|')
            echo -e "  ${WHITE}$key = $masked_value${NC}"
            ;;
        SUPABASE_URL)
            echo -e "  ${WHITE}$key = $value${NC}"
            ;;
    esac
done < <(grep -E "^(DATABASE_MODE|AUTH_MODE|SUPABASE_URL|DATABASE_URL|ENVIRONMENT|SUPABASE_KEY|SECRET_KEY)=" "backend/.env")

echo ""
echo -e "${CYAN}🚀 Next Steps:${NC}"

case $ENVIRONMENT in
    "postgresql")
        echo -e "  ${WHITE}1. Ensure PostgreSQL is running: docker-compose -f backend/docker-compose.dev.yml up -d postgres${NC}"
        echo -e "  ${WHITE}2. Start backend: cd backend && python -m uvicorn app.main:app --reload${NC}"
        echo -e "  ${WHITE}3. Register users locally through the API${NC}"
        ;;
    "supabase")
        echo -e "  ${WHITE}1. Stop local PostgreSQL if running: docker-compose -f backend/docker-compose.dev.yml down${NC}"
        echo -e "  ${WHITE}2. Start backend: cd backend && python -m uvicorn app.main:app --reload${NC}"
        echo -e "  ${WHITE}3. Use existing Supabase users or register new ones${NC}"
        ;;
    "hybrid")
        echo -e "  ${WHITE}1. Ensure PostgreSQL is running: docker-compose -f backend/docker-compose.dev.yml up -d postgres${NC}"
        echo -e "  ${WHITE}2. Start backend: cd backend && python -m uvicorn app.main:app --reload${NC}"
        echo -e "  ${WHITE}3. Authenticate with Supabase, data stored locally${NC}"
        ;;
    "production")
        echo -e "  ${YELLOW}1. This uses production Supabase configuration${NC}"
        echo -e "  ${RED}2. Make sure you want to use production data!${NC}"
        ;;
esac

echo ""