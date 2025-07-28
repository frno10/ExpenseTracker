#!/bin/bash
# Expense Tracker Setup Script for Unix/Linux/macOS

echo "Setting up Expense Tracker..."

# Backend setup
echo -e "\nSetting up Python backend..."
cd backend

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment and install dependencies
echo "Installing Python dependencies..."
source venv/bin/activate
pip install -r requirements.txt

# Run backend tests
echo "Running backend tests..."
pytest

cd ..

# Frontend setup
echo -e "\nSetting up React frontend..."
cd frontend

# Install Node.js dependencies
echo "Installing Node.js dependencies..."
npm install

# Run frontend tests
echo "Running frontend tests..."
npm test

# Build frontend
echo "Building frontend..."
npm run build

cd ..

echo -e "\nSetup complete!"
echo -e "\nTo start the development servers:"
echo "Backend:  cd backend && source venv/bin/activate && uvicorn app.main:app --reload"
echo "Frontend: cd frontend && npm run dev"
echo -e "\nTo use the CLI:"
echo "cd backend && source venv/bin/activate && python -m cli.main --help"