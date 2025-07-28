# Expense Tracker Documentation

Welcome to the comprehensive documentation for the Expense Tracker system - a modern, full-featured personal finance management application.

## 📚 Documentation Structure

- [Database Schema](./database/schema.md) - Complete database design and relationships
- [API Documentation](./api/README.md) - REST API endpoints and usage
- [Architecture Overview](./architecture/README.md) - System design and components
- [Development Guide](./development/README.md) - Setup and development workflow
- [Deployment Guide](./deployment/README.md) - Production deployment instructions

## 🏗️ System Overview

The Expense Tracker is built as a modular monolith with three primary interfaces:

- **Web Application**: React + TypeScript frontend with modern UI
- **REST API**: FastAPI backend with comprehensive endpoints
- **CLI Application**: Python Click-based command-line interface

### Key Features

- 💰 **Expense Management**: Track expenses with categories and payment methods
- 📊 **Advanced Analytics**: Multiple visualization types and insights
- 📄 **Statement Parsing**: Support for PDF, CSV, Excel, OFX, QIF formats
- 💳 **Budget Management**: Set limits and track spending against budgets
- 🔍 **Search & Filtering**: Powerful search across all expense data
- 📱 **Multi-Interface**: Consistent functionality across web, API, and CLI
- 🔒 **Security**: JWT authentication and data encryption
- 📈 **Observability**: OpenTelemetry tracing and structured logging

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker/Podman (for PostgreSQL)
- Git

### Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd expense-tracker
   ```

2. **Start the database**
   ```bash
   # Windows
   .\scripts\dev-db.ps1 start
   
   # Unix/Linux/macOS
   ./scripts/dev-db.sh start
   ```

3. **Set up the backend**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate.ps1
   pip install -r requirements.txt
   alembic upgrade head
   ```

4. **Set up the frontend**
   ```bash
   cd frontend
   npm install
   ```

5. **Run the applications**
   ```bash
   # Backend (Terminal 1)
   cd backend
   uvicorn app.main:app --reload
   
   # Frontend (Terminal 2)
   cd frontend
   npm run dev
   ```

## 📋 Project Status

This project is currently in active development. See the [task list](.kiro/specs/expense-tracker/tasks.md) for current progress.

### Completed Features ✅

- [x] Project foundation and infrastructure
- [x] Core data models and database layer
- [x] Repository pattern implementation
- [x] Database migrations with Alembic

### In Progress 🚧

- [ ] Authentication and security foundation
- [ ] Basic expense management API
- [ ] Statement parsing architecture

### Planned Features 📋

- [ ] Advanced analytics engine
- [ ] Web application frontend
- [ ] CLI application
- [ ] Real-time features
- [ ] Comprehensive security measures

## 🛠️ Technology Stack

### Backend
- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Migrations**: Alembic
- **Authentication**: JWT with Supabase Auth
- **Validation**: Pydantic v2
- **Testing**: pytest with async support

### Frontend
- **Framework**: React 18 with TypeScript
- **UI Library**: Shadcn/ui + Tailwind CSS
- **Charts**: Recharts
- **Forms**: React Hook Form
- **Testing**: Vitest + React Testing Library

### Infrastructure
- **Database**: PostgreSQL (development via Docker)
- **File Storage**: Supabase Storage
- **Observability**: OpenTelemetry
- **Deployment**: Railway/Fly.io (backend), Vercel (frontend)

## 📖 Additional Resources

- [Requirements Document](.kiro/specs/expense-tracker/requirements.md)
- [Design Document](.kiro/specs/expense-tracker/design.md)
- [Task List](.kiro/specs/expense-tracker/tasks.md)
- [Changelog](../CHANGELOG.md)

## 🤝 Contributing

This project follows a spec-driven development approach. Please refer to the requirements and design documents before making changes.

## 📄 License

[Add your license information here]