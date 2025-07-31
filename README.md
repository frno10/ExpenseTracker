# Expense Tracker

A comprehensive personal finance management system with authentication, expense tracking, and category management.

## 🚀 Quick Start

**For Development Setup**: See [DEVELOPMENT.md](DEVELOPMENT.md) for detailed setup instructions.

### Windows Development

```powershell
# Activate virtual environment
& .venv\Scripts\Activate.ps1

# Navigate to backend
cd backend

# Start the server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**API will be available at**: <http://localhost:8000>  
**API Documentation**: <http://localhost:8000/docs>

## 📁 Project Structure

```
expense-tracker/
├── backend/
│   ├── app/
│   │   └── main.py          # Single main application (ENTRY POINT)
│   ├── .env                 # Environment configuration
│   └── requirements.txt     # Python dependencies
├── frontend/                # React TypeScript frontend
├── docs/                    # Documentation and specs
└── DEVELOPMENT.md           # Detailed setup guide
```

## ✨ Features

- **Authentication**: User registration and login with Supabase
- **Expense Management**: Create, read, update, delete expenses
- **Categories**: Organize expenses by category with summaries
- **User Isolation**: Each user's data is completely separate
- **REST API**: Full RESTful API with OpenAPI documentation
- **Real-time**: Built with FastAPI for high performance

## 🛠 Technology Stack

- **Backend**: Python, FastAPI, Supabase Auth, Pydantic
- **Database**: PostgreSQL (via Supabase)
- **Frontend**: React, TypeScript, Tailwind CSS, Shadcn/ui
- **Development**: Python virtual environment, hot reload

## 📚 API Endpoints

### Authentication

- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login user  
- `GET /api/v1/auth/me` - Get current user

### Expenses

- `POST /api/v1/expenses` - Create expense
- `GET /api/v1/expenses` - List all expenses
- `GET /api/v1/expenses/{id}` - Get specific expense
- `PUT /api/v1/expenses/{id}` - Update expense
- `DELETE /api/v1/expenses/{id}` - Delete expense

### Analytics

- `GET /api/v1/categories` - Category summaries
- `GET /api/v1/summary` - Expense overview

## 🔧 Configuration

The application uses environment variables in `backend/.env`:

```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
SECRET_KEY=your_secret_key
DEBUG=true
```

## 📖 Documentation

- [DEVELOPMENT.md](DEVELOPMENT.md) - Complete development setup guide
- [API Docs](http://localhost:8000/docs) - Interactive API documentation (when running)
- [Supabase Dashboard](https://supabase.com/dashboard) - Database and auth management

## 🤝 Contributing

1. Follow the setup in [DEVELOPMENT.md](DEVELOPMENT.md)
2. Make your changes
3. Test the API endpoints
4. Submit a pull request

## 📄 License

This project is licensed under the MIT License.
