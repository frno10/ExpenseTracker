"""
Expense Tracker - Complete FastAPI application with Supabase authentication.
This is the main and only application entry point.
"""
from fastapi import FastAPI, HTTPException, status, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import time
from pydantic import BaseModel
from typing import Optional
import os
import logging
import sys
from supabase import create_client, Client
import jwt
from datetime import datetime
from dotenv import load_dotenv
import uuid

# Import proper authentication system
from app.core.auth import get_current_user as get_current_user_proper
from app.core.database import get_db, init_db
from app.core.config import settings
from app.models import UserTable

# Load environment variables
load_dotenv()

# Configure logging (Windows-compatible)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Set console handler encoding for Windows
for handler in logging.getLogger().handlers:
    if isinstance(handler, logging.StreamHandler):
        handler.stream = sys.stdout

# Create FastAPI app
app = FastAPI(
    title="Expense Tracker API",
    description="A comprehensive expense management system",
    version="1.0.0",
)

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    from app.core.config import settings
    
    logger.info(f"[STARTUP] Database mode: {settings.database_mode}")
    
    if settings.database_mode == "postgresql":
        # Direct PostgreSQL connection with SQLAlchemy
        try:
            await init_db()
            logger.info("[STARTUP] PostgreSQL database initialized successfully")
        except Exception as e:
            logger.error(f"[STARTUP] PostgreSQL initialization failed: {e}")
            logger.error("[STARTUP] Application startup failed - check database connection")
            raise
            
    elif settings.database_mode == "supabase_rest":
        # Supabase REST API mode
        logger.info("[STARTUP] Using Supabase REST API for database operations")
        try:
            # Test Supabase connection
            test_response = supabase.table('users').select('id').limit(1).execute()
            logger.info("[STARTUP] Supabase REST API connection verified")
        except Exception as e:
            logger.error(f"[STARTUP] Supabase REST API test failed: {e}")
            logger.error("[STARTUP] Application startup failed - check Supabase connection")
            raise
            
    else:
        logger.error(f"[STARTUP] Invalid database mode: {settings.database_mode}")
        logger.error("[STARTUP] Valid options: postgresql, supabase_rest")
        raise ValueError(f"Invalid database mode: {settings.database_mode}")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://127.0.0.1:3000",
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:5173",
        "https://*.netlify.app",  # Netlify domains
        "https://incandescent-pixie-7c87ba.netlify.app"  # Your Netlify URL
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Log incoming request
    logger.info(f"[REQUEST] {request.method} {request.url.path}")
    logger.info(f"[REQUEST] Origin: {request.headers.get('origin', 'No origin')}")
    logger.info(f"[REQUEST] Content-Type: {request.headers.get('content-type', 'No content-type')}")
    logger.info(f"[REQUEST] User-Agent: {request.headers.get('user-agent', 'No user-agent')[:100]}")
    
    # Process request
    response = await call_next(request)
    
    # Log response
    process_time = time.time() - start_time
    logger.info(f"[RESPONSE] {response.status_code} ({process_time:.3f}s)")
    
    return response

# Log startup information
logger.info("[STARTUP] Expense Tracker API starting up...")
logger.info(f"[STARTUP] CORS enabled for: localhost:3000, localhost:5173 (and 127.0.0.1 variants)")
logger.info(f"[STARTUP] Supabase URL: {os.getenv('SUPABASE_URL')}")
logger.info(f"[STARTUP] Supabase Key configured: {bool(os.getenv('SUPABASE_KEY'))}")

# Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

# Security
security = HTTPBearer(auto_error=False)

# Pydantic models
class UserRegister(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None

class UserLogin(BaseModel):
    email: str
    password: str

class ResendConfirmationRequest(BaseModel):
    email: str

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    created_at: str

class AuthResponse(BaseModel):
    user: UserResponse
    access_token: str
    token_type: str = "bearer"

# Expense models
class ExpenseCreate(BaseModel):
    amount: float
    description: str
    category: str
    date: Optional[str] = None

class ExpenseResponse(BaseModel):
    id: str
    amount: float
    description: str
    category: str
    date: str
    created_at: str
    user_id: str

class CategoryResponse(BaseModel):
    name: str
    total_expenses: float
    expense_count: int

# Categories for expense classification
categories = ["Food", "Transportation", "Entertainment", "Utilities", "Healthcare", "Shopping", "Other"]

# Auth dependency for Supabase JWT tokens
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user from Supabase JWT token."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        token = credentials.credentials
        
        # Try Supabase JWT verification
        try:
            user_response = supabase.auth.get_user(token)
            if user_response.user:
                return {
                    "id": user_response.user.id,
                    "email": user_response.user.email
                }
        except Exception as supabase_error:
            logger.debug(f"Supabase token verification failed: {supabase_error}")
        
        # Try manual JWT decoding as fallback
        try:
            payload = jwt.decode(token, supabase_key, algorithms=["HS256"], options={"verify_signature": False})
            user_id = payload.get("sub")
            email = payload.get("email")
            
            if user_id and email:
                return {"id": user_id, "email": email}
        except Exception as jwt_error:
            logger.debug(f"Manual JWT decoding failed: {jwt_error}")
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.debug(f"Token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

# Routes
@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Expense Tracker API is running!"}

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "message": "API is operational"}

@app.post("/api/v1/auth/register", response_model=AuthResponse)
async def register(user_data: UserRegister):
    """Register a new user."""
    logger.info(f"[AUTH] Registration attempt for email: {user_data.email}")
    logger.info(f"[AUTH] Full name provided: {user_data.full_name}")
    logger.info(f"[AUTH] Password length: {len(user_data.password) if user_data.password else 0}")
    
    try:
        # Log Supabase configuration
        logger.info(f"[SUPABASE] URL: {supabase_url}")
        logger.info(f"[SUPABASE] Key configured: {bool(supabase_key)}")
        
        # Prepare registration data
        registration_data = {
            "email": user_data.email,
            "password": user_data.password,
            "options": {
                "data": {
                    "full_name": user_data.full_name
                }
            }
        }
        logger.info(f"[SUPABASE] Sending registration data for: {registration_data['email']}")
        
        # Register user with Supabase Auth
        response = supabase.auth.sign_up(registration_data)
        
        logger.info(f"[SUPABASE] Response received")
        logger.info(f"[SUPABASE] User created: {bool(response.user)}")
        logger.info(f"[SUPABASE] Session created: {bool(response.session)}")
        
        if response.user:
            logger.info(f"[SUCCESS] User registered successfully: {response.user.id}")
            logger.info(f"[SUCCESS] User email: {response.user.email}")
            
            user_response = UserResponse(
                id=response.user.id,
                email=response.user.email,
                full_name=user_data.full_name,
                created_at=datetime.now().isoformat()
            )
            
            auth_response = AuthResponse(
                user=user_response,
                access_token=response.session.access_token if response.session else "",
                token_type="bearer"
            )
            
            logger.info(f"[SUCCESS] Registration completed successfully for: {user_data.email}")
            return auth_response
        else:
            logger.error(f"[ERROR] Supabase returned no user object for: {user_data.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration failed - no user created"
            )
            
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"[ERROR] Registration exception for {user_data.email}: {type(e).__name__}: {str(e)}")
        logger.error(f"[ERROR] Exception details: {repr(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration failed: {str(e)}"
        )



@app.post("/api/v1/auth/login", response_model=AuthResponse)
async def login(user_data: UserLogin):
    """Login user."""
    logger.info(f"[AUTH] Login attempt for email: {user_data.email}")
    logger.info(f"[AUTH] Password length: {len(user_data.password) if user_data.password else 0}")
    
    try:
        # Prepare login data
        login_data = {
            "email": user_data.email,
            "password": user_data.password
        }
        logger.info(f"[SUPABASE] Sending login request for: {login_data['email']}")
        
        # Login with Supabase Auth
        response = supabase.auth.sign_in_with_password(login_data)
        
        logger.info(f"[SUPABASE] Login response received")
        logger.info(f"[SUPABASE] User object: {bool(response.user)}")
        logger.info(f"[SUPABASE] Session object: {bool(response.session)}")
        
        if response.user:
            logger.info(f"[SUPABASE] User ID: {response.user.id}")
            logger.info(f"[SUPABASE] User email: {response.user.email}")
            logger.info(f"[SUPABASE] User confirmed: {getattr(response.user, 'email_confirmed_at', 'N/A')}")
        
        if response.session:
            logger.info(f"[SUPABASE] Access token present: {bool(response.session.access_token)}")
            logger.info(f"[SUPABASE] Token type: {getattr(response.session, 'token_type', 'N/A')}")
        
        if response.user and response.session:
            logger.info(f"[SUCCESS] Login successful for: {response.user.email}")
            
            user_response = UserResponse(
                id=response.user.id,
                email=response.user.email,
                full_name=response.user.user_metadata.get("full_name") if response.user.user_metadata else None,
                created_at=response.user.created_at
            )
            
            auth_response = AuthResponse(
                user=user_response,
                access_token=response.session.access_token,
                token_type="bearer"
            )
            
            logger.info(f"[SUCCESS] Login completed successfully for: {user_data.email}")
            return auth_response
        elif response.user and not response.session:
            # User exists but no session - likely email not confirmed
            email_confirmed = getattr(response.user, 'email_confirmed_at', None)
            logger.error(f"[ERROR] User exists but no session created")
            logger.error(f"[ERROR] Email confirmed at: {email_confirmed}")
            
            if not email_confirmed:
                logger.info(f"[AUTH] Email not confirmed for: {user_data.email}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Please check your email and confirm your account before logging in."
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication failed. Please try again."
                )
        else:
            logger.error(f"[ERROR] Login failed - missing user or session")
            logger.error(f"[ERROR] User present: {bool(response.user)}")
            logger.error(f"[ERROR] Session present: {bool(response.session)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password. Please check your credentials and try again."
            )
            
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"[ERROR] Login exception for {user_data.email}: {type(e).__name__}: {str(e)}")
        logger.error(f"[ERROR] Exception details: {repr(e)}")
        
        # Parse Supabase error messages to provide better user feedback
        error_message = str(e).lower()
        
        if "email not confirmed" in error_message or "email_not_confirmed" in error_message:
            logger.info(f"[AUTH] Email not confirmed for: {user_data.email}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Please check your email and confirm your account before logging in."
            )
        elif "invalid login credentials" in error_message or "invalid_credentials" in error_message:
            logger.info(f"[AUTH] Invalid credentials for: {user_data.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password. Please check your credentials and try again."
            )
        elif "user not found" in error_message or "user_not_found" in error_message:
            logger.info(f"[AUTH] User not found: {user_data.email}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No account found with this email address. Please register first."
            )
        elif "too many requests" in error_message or "rate_limit" in error_message:
            logger.info(f"[AUTH] Rate limit exceeded for: {user_data.email}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts. Please wait a moment and try again."
            )
        else:
            # Generic error for unknown issues
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Login failed. Please check your credentials and try again."
            )

@app.post("/api/v1/auth/resend-confirmation")
async def resend_confirmation(request: ResendConfirmationRequest):
    """Resend email confirmation."""
    logger.info(f"[AUTH] Resend confirmation request for: {request.email}")
    
    try:
        # Resend confirmation email
        response = supabase.auth.resend({
            "type": "signup",
            "email": request.email
        })
        
        logger.info(f"[SUCCESS] Confirmation email resent to: {request.email}")
        return {
            "message": "Confirmation email sent. Please check your inbox and spam folder.",
            "email": request.email
        }
        
    except Exception as e:
        logger.error(f"[ERROR] Failed to resend confirmation to {request.email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to resend confirmation email. Please try again later."
        )

@app.get("/api/v1/auth/me", response_model=UserResponse)
async def get_me(current_user = Depends(get_current_user)):
    """Get current user info."""
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        full_name=None,
        created_at=datetime.now().isoformat()
    )

@app.get("/api/v1/test")
async def test_endpoint(current_user = Depends(get_current_user)):
    """Test authenticated endpoint."""
    return {
        "message": "API test successful", 
        "version": "1.0.0",
        "user": current_user
    }

# Expense endpoints
@app.post("/api/v1/expenses", response_model=ExpenseResponse)
async def create_expense(expense: ExpenseCreate, current_user = Depends(get_current_user)):
    """Create a new expense."""
    user_id = current_user["id"]
    now = datetime.now().isoformat()
    
    expense_data = {
        "user_id": user_id,
        "amount": expense.amount,
        "description": expense.description,
        "category": expense.category,
        "date": expense.date or now.split("T")[0]
    }
    
    try:
        result = supabase.table('expenses').insert(expense_data).execute()
        if result.data and len(result.data) > 0:
            created_expense = result.data[0]
            return ExpenseResponse(
                id=created_expense["id"],
                amount=created_expense["amount"],
                description=created_expense["description"],
                category=created_expense["category"],
                date=created_expense["date"],
                created_at=created_expense["created_at"],
                user_id=created_expense["user_id"]
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to create expense")
    except Exception as e:
        logger.error(f"Error creating expense: {e}")
        raise HTTPException(status_code=500, detail="Failed to create expense")

@app.get("/api/v1/expenses")
async def get_expenses(current_user = Depends(get_current_user)):
    """Get all expenses for current user."""
    user_id = current_user["id"]
    
    try:
        result = supabase.table('expenses').select('*').eq('user_id', user_id).execute()
        return result.data or []
    except Exception as e:
        logger.error(f"Error fetching expenses from Supabase: {e}")
        return []

@app.get("/api/v1/expenses/{expense_id}", response_model=ExpenseResponse)
async def get_expense(expense_id: str, current_user = Depends(get_current_user)):
    """Get a specific expense."""
    user_id = current_user["id"]
    
    try:
        result = supabase.table('expenses').select('*').eq('id', expense_id).eq('user_id', user_id).execute()
        if result.data and len(result.data) > 0:
            expense = result.data[0]
            return ExpenseResponse(**expense)
        else:
            raise HTTPException(status_code=404, detail="Expense not found")
    except Exception as e:
        logger.error(f"Error fetching expense: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch expense")

@app.put("/api/v1/expenses/{expense_id}", response_model=ExpenseResponse)
async def update_expense(expense_id: str, expense: ExpenseCreate, current_user = Depends(get_current_user)):
    """Update an expense."""
    user_id = current_user["id"]
    
    try:
        # First check if expense exists and belongs to user
        existing = supabase.table('expenses').select('*').eq('id', expense_id).eq('user_id', user_id).execute()
        if not existing.data or len(existing.data) == 0:
            raise HTTPException(status_code=404, detail="Expense not found")
        
        # Update the expense
        update_data = {
            "amount": expense.amount,
            "description": expense.description,
            "category": expense.category,
            "date": expense.date or existing.data[0]["date"]
        }
        
        result = supabase.table('expenses').update(update_data).eq('id', expense_id).eq('user_id', user_id).execute()
        if result.data and len(result.data) > 0:
            updated_expense = result.data[0]
            return ExpenseResponse(**updated_expense)
        else:
            raise HTTPException(status_code=500, detail="Failed to update expense")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating expense: {e}")
        raise HTTPException(status_code=500, detail="Failed to update expense")

@app.delete("/api/v1/expenses/{expense_id}")
async def delete_expense(expense_id: str, current_user = Depends(get_current_user)):
    """Delete an expense."""
    user_id = current_user["id"]
    
    try:
        # First check if expense exists and belongs to user
        existing = supabase.table('expenses').select('id').eq('id', expense_id).eq('user_id', user_id).execute()
        if not existing.data or len(existing.data) == 0:
            raise HTTPException(status_code=404, detail="Expense not found")
        
        # Delete the expense
        result = supabase.table('expenses').delete().eq('id', expense_id).eq('user_id', user_id).execute()
        return {"message": "Expense deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting expense: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete expense")

# Category endpoints
@app.get("/api/v1/categories")
async def get_categories(current_user = Depends(get_current_user)):
    """Get all categories with expense summaries for current user."""
    user_id = current_user["id"]
    
    try:
        # Get all expenses for user
        result = supabase.table('expenses').select('*').eq('user_id', user_id).execute()
        user_expenses = result.data or []
        
        category_summaries = []
        for category in categories:
            category_expenses = [exp for exp in user_expenses if exp["category"] == category]
            total_amount = sum(float(exp["amount"]) for exp in category_expenses)
            
            category_summaries.append(CategoryResponse(
                name=category,
                total_expenses=total_amount,
                expense_count=len(category_expenses)
            ))
        
        return category_summaries
    except Exception as e:
        logger.error(f"Error fetching categories: {e}")
        return []

@app.get("/api/v1/summary")
async def get_summary(current_user = Depends(get_current_user)):
    """Get expense summary for current user."""
    user_id = current_user["id"]
    
    try:
        # Get all expenses for user
        result = supabase.table('expenses').select('*').eq('user_id', user_id).order('created_at', desc=True).execute()
        user_expenses = result.data or []
        
        total_expenses = len(user_expenses)
        total_amount = sum(float(exp["amount"]) for exp in user_expenses)
        categories_used = len(set(exp["category"] for exp in user_expenses)) if user_expenses else 0
        
        return {
            "total_expenses": total_expenses,
            "total_amount": total_amount,
            "categories_used": categories_used,
            "recent_expenses": user_expenses[:5]  # First 5 (most recent due to desc order)
        }
    except Exception as e:
        logger.error(f"Error fetching summary: {e}")
        return {
            "total_expenses": 0,
            "total_amount": 0,
            "categories_used": 0,
            "recent_expenses": []
        }

# Additional endpoints to prevent frontend errors
@app.get("/api/budgets")
async def get_budgets(active_only: bool = False, current_user = Depends(get_current_user)):
    """Get budgets (placeholder endpoint)."""
    return []

@app.get("/api/budgets/alerts")
async def get_budget_alerts(current_user = Depends(get_current_user)):
    """Get budget alerts (placeholder endpoint)."""
    return []

@app.get("/api/recurring-expenses")
async def get_recurring_expenses(current_user = Depends(get_current_user)):
    """Get recurring expenses (placeholder endpoint)."""
    return []

@app.get("/api/recurring-expenses/notifications")
async def get_recurring_notifications(current_user = Depends(get_current_user)):
    """Get recurring expense notifications (placeholder endpoint)."""
    return []

@app.get("/api/analytics/dashboard")
async def get_analytics_dashboard(period_days: int = 30, current_user = Depends(get_current_user)):
    """Get analytics dashboard data (placeholder endpoint)."""
    return {
        "total_expenses": 0,
        "monthly_spending": 0,
        "categories": [],
        "trends": []
    }

# Statement Import endpoints with real PDF parsing functionality
from fastapi import UploadFile, File, Form
import tempfile
import os
import uuid
from typing import Dict, Any

# In-memory storage for uploaded files and parse results
uploaded_files: Dict[str, Dict[str, Any]] = {}
parse_results: Dict[str, Dict[str, Any]] = {}

@app.post("/api/statement-import/upload")
async def upload_statement(
    file: UploadFile = File(...),
    bank_hint: Optional[str] = Form(None),
    current_user = Depends(get_current_user)
):
    """Upload a statement file for processing."""
    try:
        # Basic file validation
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Check file size (50MB limit)
        if file.size and file.size > 50 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File size exceeds 50MB limit")
        
        # Check file extension
        file_extension = file.filename.split('.')[-1].lower()
        supported_extensions = ['pdf', 'csv', 'xlsx', 'xls', 'ofx', 'qif', 'txt']
        
        if file_extension not in supported_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file format: {file_extension}. Supported: {', '.join(supported_extensions)}"
            )
        
        # Generate unique upload ID
        upload_id = str(uuid.uuid4())
        
        # Save file temporarily
        temp_file = tempfile.NamedTemporaryFile(
            delete=False, 
            suffix=f".{file_extension}",
            prefix=f"statement_{current_user['id']}_"
        )
        
        # Read and save file content
        content = await file.read()
        temp_file.write(content)
        temp_file.close()
        
        # Store upload info
        uploaded_files[upload_id] = {
            "user_id": current_user["id"],
            "filename": file.filename,
            "file_size": len(content),
            "file_path": temp_file.name,
            "file_type": file_extension,
            "bank_hint": bank_hint,
            "upload_time": datetime.now().isoformat()
        }
        
        # Detect parser
        detected_parser = None
        if file_extension == "pdf":
            detected_parser = "pdf_parser"
        elif file_extension in ["csv", "txt"]:
            detected_parser = "csv_parser"
        elif file_extension in ["xlsx", "xls"]:
            detected_parser = "excel_parser"
        elif file_extension in ["ofx", "qfx"]:
            detected_parser = "ofx_parser"
        elif file_extension == "qif":
            detected_parser = "qif_parser"
        
        return {
            "upload_id": upload_id,
            "filename": file.filename,
            "file_size": len(content),
            "file_type": file_extension,
            "supported_format": True,
            "detected_parser": detected_parser,
            "validation_errors": []
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.post("/api/statement-import/preview/{upload_id}")
async def preview_statement(upload_id: str, current_user = Depends(get_current_user)):
    """Preview parsed transactions from uploaded statement."""
    try:
        # Check if upload exists
        if upload_id not in uploaded_files:
            raise HTTPException(status_code=404, detail="Upload not found")
        
        upload_info = uploaded_files[upload_id]
        
        # Verify user owns this upload
        if upload_info["user_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Parse the file using our PDF parser
        if upload_info["file_type"] == "pdf":
            from app.parsers.pdf_parser import PDFParser
            from app.parsers.config import config_manager
            
            parser = PDFParser()
            
            # Load ČSOB configuration if bank hint suggests it
            if upload_info.get("bank_hint") and "csob" in upload_info["bank_hint"].lower():
                csob_config = config_manager.load_bank_config("csob_slovakia")
                if csob_config and "pdf_config" in csob_config:
                    parser.config.settings.update(csob_config["pdf_config"])
            
            # Parse the PDF
            result = await parser.parse(upload_info["file_path"])
            
            # Convert transactions to API format
            sample_transactions = []
            for i, tx in enumerate(result.transactions[:10]):  # First 10 for preview
                sample_transactions.append({
                    "index": i,
                    "date": tx.date.isoformat(),
                    "description": tx.description,
                    "amount": float(tx.amount),
                    "merchant": tx.merchant,
                    "category": tx.category,
                    "account": tx.account or "Unknown",
                    "reference": tx.reference or ""
                })
            
            # Store parse result for later use
            parse_results[upload_id] = {
                "success": result.success,
                "transactions": result.transactions,
                "errors": result.errors,
                "warnings": result.warnings,
                "metadata": result.metadata
            }
            
            return {
                "upload_id": upload_id,
                "success": result.success,
                "transaction_count": len(result.transactions),
                "sample_transactions": sample_transactions,
                "errors": result.errors,
                "warnings": result.warnings,
                "metadata": result.metadata
            }
        else:
            # For non-PDF files, return a placeholder for now
            return {
                "upload_id": upload_id,
                "success": False,
                "transaction_count": 0,
                "sample_transactions": [],
                "errors": [f"Parser for {upload_info['file_type']} files not implemented yet"],
                "warnings": [],
                "metadata": {"file_type": upload_info["file_type"]}
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Preview error: {e}")
        raise HTTPException(status_code=500, detail=f"Preview failed: {str(e)}")

@app.post("/api/statement-import/analyze-duplicates/{upload_id}")
async def analyze_duplicates(upload_id: str, current_user = Depends(get_current_user)):
    """Analyze transactions for potential duplicates."""
    try:
        # Check if parse result exists
        if upload_id not in parse_results:
            raise HTTPException(status_code=404, detail="Parse result not found. Please preview first.")
        
        parse_result = parse_results[upload_id]
        
        # Simple duplicate analysis - check against existing expenses
        try:
            result = supabase.table('expenses').select('*').eq('user_id', current_user["id"]).execute()
            user_expenses = result.data or []
        except Exception as e:
            logger.error(f"Error fetching expenses for duplicate analysis: {e}")
            user_expenses = []
        
        analysis = []
        for i, tx in enumerate(parse_result["transactions"]):
            # Check for potential duplicates based on date, amount, and description
            potential_duplicates = []
            is_likely_duplicate = False
            
            for expense in user_expenses:
                # Simple matching logic
                date_match = expense.get("date") == tx.date.isoformat()[:10]
                amount_match = abs(float(expense.get("amount", 0)) - float(tx.amount)) < 0.01
                desc_similarity = tx.description.lower() in expense.get("description", "").lower()
                
                if date_match and amount_match:
                    is_likely_duplicate = True
                    potential_duplicates.append({
                        "expense_id": expense.get("id"),
                        "match_score": 0.9,
                        "match_reasons": ["date_match", "amount_match"]
                    })
                elif desc_similarity and amount_match:
                    potential_duplicates.append({
                        "expense_id": expense.get("id"),
                        "match_score": 0.7,
                        "match_reasons": ["description_similarity", "amount_match"]
                    })
            
            analysis.append({
                "transaction_index": i,
                "transaction": {
                    "date": tx.date.isoformat(),
                    "description": tx.description,
                    "amount": float(tx.amount),
                    "merchant": tx.merchant
                },
                "is_likely_duplicate": is_likely_duplicate,
                "confidence_score": 0.9 if is_likely_duplicate else 0.1,
                "potential_duplicates": potential_duplicates
            })
        
        likely_duplicates = sum(1 for item in analysis if item["is_likely_duplicate"])
        
        return {
            "upload_id": upload_id,
            "total_transactions": len(analysis),
            "likely_duplicates": likely_duplicates,
            "analysis": analysis
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Duplicate analysis error: {e}")
        raise HTTPException(status_code=500, detail=f"Duplicate analysis failed: {str(e)}")

@app.post("/api/statement-import/confirm/{upload_id}")
async def confirm_import(upload_id: str, request: dict, current_user = Depends(get_current_user)):
    """Confirm and execute the statement import."""
    try:
        # Check if parse result exists
        if upload_id not in parse_results:
            raise HTTPException(status_code=404, detail="Parse result not found")
        
        parse_result = parse_results[upload_id]
        selected_transactions = request.get("selected_transactions", [])
        
        # If no specific transactions selected, import all
        if not selected_transactions:
            selected_transactions = list(range(len(parse_result["transactions"])))
        
        # Import selected transactions as expenses
        user_id = current_user["id"]
        imported_count = 0
        skipped_count = 0
        errors = []
        
        for i in selected_transactions:
            if i >= len(parse_result["transactions"]):
                continue
                
            tx = parse_result["transactions"][i]
            
            try:
                # Create expense from transaction
                expense_data = {
                    "user_id": user_id,
                    "description": tx.description,
                    "amount": float(tx.amount),
                    "category": tx.category or "Other",
                    "date": tx.date.isoformat()[:10]
                }
                
                # Save to Supabase using REST API
                result = supabase.table('expenses').insert(expense_data).execute()
                if result.data:
                    imported_count += 1
                else:
                    errors.append(f"Failed to save transaction {i} to Supabase")
                    skipped_count += 1
                
            except Exception as e:
                errors.append(f"Failed to import transaction {i}: {str(e)}")
                skipped_count += 1
        
        # Clean up temporary file
        upload_info = uploaded_files.get(upload_id)
        if upload_info and os.path.exists(upload_info["file_path"]):
            try:
                os.unlink(upload_info["file_path"])
            except:
                pass  # Ignore cleanup errors
        
        # Clean up stored data
        if upload_id in uploaded_files:
            del uploaded_files[upload_id]
        if upload_id in parse_results:
            del parse_results[upload_id]
        
        return {
            "import_id": str(uuid.uuid4()),
            "success": imported_count > 0,
            "imported_count": imported_count,
            "skipped_count": skipped_count,
            "duplicate_count": 0,  # We don't auto-skip duplicates
            "errors": errors
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Import confirmation error: {e}")
        raise HTTPException(status_code=500, detail=f"Import confirmation failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)