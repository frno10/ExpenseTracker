# Expense Tracker

A comprehensive personal finance management system with web, API, and CLI interfaces.

## Project Structure

```
expense-tracker/
├── backend/                 # Python FastAPI backend
│   ├── app/                # Main application code
│   │   ├── api/           # API routes
│   │   ├── core/          # Configuration and utilities
│   │   ├── models/        # Data models
│   │   ├── repositories/  # Data access layer
│   │   └── services/      # Business logic
│   ├── cli/               # Command line interface
│   ├── tests/             # Backend tests
│   └── requirements.txt   # Python dependencies
├── frontend/              # React TypeScript frontend
│   ├── src/              # Source code
│   │   ├── components/   # React components
│   │   ├── pages/        # Page components
│   │   ├── lib/          # Utilities and configurations
│   │   └── test/         # Frontend tests
│   └── package.json      # Node.js dependencies
└── .kiro/                # Kiro specifications
    └── specs/
        └── expense-tracker/
```

## Getting Started

### Quick Setup

**Windows:**
```powershell
.\setup.ps1
```

**Unix/Linux/macOS:**
```bash
chmod +x setup.sh
./setup.sh
```

### Manual Setup

#### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate.ps1
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Copy environment variables:
   ```bash
   cp .env.example .env  # On Windows: copy .env.example .env
   ```

5. Run the development server:
   ```bash
   uvicorn app.main:app --reload
   ```

#### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Copy environment variables:
   ```bash
   cp .env.example .env  # On Windows: copy .env.example .env
   ```

4. Run the development server:
   ```bash
   npm run dev
   ```

### CLI Usage

From the backend directory with the virtual environment activated:

```bash
python -m cli.main --help
python -m cli.main add --amount 25.50 --description "Lunch" --category "Food"
python -m cli.main report --period monthly --format table
```

## Technology Stack

- **Backend**: Python, FastAPI, SQLAlchemy, Pydantic
- **Frontend**: React, TypeScript, Tailwind CSS, Shadcn/ui
- **Database**: PostgreSQL (via Supabase)
- **CLI**: Python Click
- **Testing**: pytest (backend), Vitest (frontend)
- **Development**: Black, mypy, pre-commit hooks

## Features

- Multi-interface access (Web, API, CLI)
- Expense tracking and categorization
- Budget management
- Statement parsing (PDF, CSV, Excel, OFX, QIF)
- Advanced analytics and reporting
- Real-time updates
- Comprehensive observability

## Development

### Running Tests

Backend:
```bash
cd backend
pytest
```

Frontend:
```bash
cd frontend
npm test
```

### Code Formatting

Backend:
```bash
cd backend
black .
mypy .
```

Frontend:
```bash
cd frontend
npm run lint
```

## Environment Variables

### Backend (.env)
- `DATABASE_URL`: PostgreSQL connection string
- `SUPABASE_URL`: Supabase project URL
- `SUPABASE_KEY`: Supabase anon key
- `SECRET_KEY`: JWT secret key

### Frontend (.env)
- `VITE_SUPABASE_URL`: Supabase project URL
- `VITE_SUPABASE_ANON_KEY`: Supabase anon key