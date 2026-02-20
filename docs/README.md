# Expense Tracker Documentation

Documentation for the Expense Tracker system - a personal finance management application built with FastAPI and React.

## Documentation Structure

- [Database Schema](./database/schema.md) - Database design and relationships
- [Architecture Overview](./architecture/README.md) - System design and components
- [Development Guide](./development/README.md) - Setup and development workflow
- [Deployment Guide](./DEPLOYMENT.md) - Production deployment instructions
- [Free Deployment](./FREE_DEPLOYMENT.md) - Free tier deployment guide
- [Supabase Auth](./SUPABASE_AUTHENTICATION.md) - Authentication system guide

## System Overview

The Expense Tracker is designed as a modular monolith with three interfaces:

- **Web Application**: React + TypeScript frontend with Shadcn/ui
- **REST API**: FastAPI backend with OpenAPI documentation
- **CLI Application**: Python Click-based command-line interface (standalone, not connected to API)

## Project Status

See [PROJECT_ASSESSMENT.md](../PROJECT_ASSESSMENT.md) for a comprehensive, honest assessment.

### Working End-to-End
- [x] User authentication (Supabase Auth)
- [x] Expense CRUD operations
- [x] Category management with summaries
- [x] PDF statement import (CSOB bank parser)
- [x] Dashboard with basic stats
- [x] Health check endpoint

### Coded but Not Connected to Running App
- [ ] Budget management (service + API + frontend exist)
- [ ] Recurring expenses (service + API + frontend exist)
- [ ] Advanced analytics (service + API + frontend exist)
- [ ] Payment methods / accounts
- [ ] Notes and attachments
- [ ] Data export (CSV, PDF, Excel)
- [ ] WebSocket real-time updates
- [ ] Security middleware (CSRF, rate limiting, headers)
- [ ] Audit logging
- [ ] CLI integration with API

### Not Implemented
- [ ] Performance optimizations (Task 21)
- [ ] Redis caching
- [ ] OpenTelemetry (dependency not installed)
- [ ] Chart visualizations
- [ ] CI/CD pipeline
- [ ] Database migration management
- [ ] Frontend testing (1 test exists)
- [ ] Deployment and documentation finalization (Task 23)

## Technology Stack

### Backend
- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL (via Supabase)
- **Authentication**: JWT with Supabase Auth
- **Validation**: Pydantic v2
- **Testing**: pytest with async support

### Frontend
- **Framework**: React 18 with TypeScript
- **UI Library**: Shadcn/ui + Tailwind CSS
- **Forms**: React Hook Form

## Additional Resources

- [Requirements Document](../.kiro/specs/expense-tracker/requirements.md)
- [Design Document](../.kiro/specs/expense-tracker/design.md)
- [Task List](../.kiro/specs/expense-tracker/tasks.md)
- [Changelog](../CHANGELOG.md)

## Contributing

This project follows a spec-driven development approach. Please refer to the requirements and design documents before making changes.
