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

# Simple in-memory storage for development (per user)
expenses_db = {}  # user_id -> {expense_id -> expense_data}
categories = ["Food", "Transportation", "Entertainment", "Utilities", "Healthcare", "Shopping", "Other"]

# Auth dependency
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user from JWT token."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        # Verify JWT token with Supabase
        token = credentials.credentials
        payload = jwt.decode(token, supabase_key, algorithms=["HS256"])
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        return {"id": user_id, "email": payload.get("email")}
    except jwt.InvalidTokenError:
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
    import uuid
    
    user_id = current_user["id"]
    expense_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    
    # Initialize user expenses if not exists
    if user_id not in expenses_db:
        expenses_db[user_id] = {}
    
    expense_data = {
        "id": expense_id,
        "amount": expense.amount,
        "description": expense.description,
        "category": expense.category,
        "date": expense.date or now.split("T")[0],
        "created_at": now,
        "user_id": user_id
    }
    
    expenses_db[user_id][expense_id] = expense_data
    return ExpenseResponse(**expense_data)

@app.get("/api/v1/expenses")
async def get_expenses(current_user = Depends(get_current_user)):
    """Get all expenses for current user."""
    user_id = current_user["id"]
    user_expenses = expenses_db.get(user_id, {})
    return list(user_expenses.values())

@app.get("/api/v1/expenses/{expense_id}", response_model=ExpenseResponse)
async def get_expense(expense_id: str, current_user = Depends(get_current_user)):
    """Get a specific expense."""
    user_id = current_user["id"]
    user_expenses = expenses_db.get(user_id, {})
    
    if expense_id not in user_expenses:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    return ExpenseResponse(**user_expenses[expense_id])

@app.put("/api/v1/expenses/{expense_id}", response_model=ExpenseResponse)
async def update_expense(expense_id: str, expense: ExpenseCreate, current_user = Depends(get_current_user)):
    """Update an expense."""
    user_id = current_user["id"]
    user_expenses = expenses_db.get(user_id, {})
    
    if expense_id not in user_expenses:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    expense_data = user_expenses[expense_id]
    expense_data.update({
        "amount": expense.amount,
        "description": expense.description,
        "category": expense.category,
        "date": expense.date or expense_data["date"]
    })
    
    return ExpenseResponse(**expense_data)

@app.delete("/api/v1/expenses/{expense_id}")
async def delete_expense(expense_id: str, current_user = Depends(get_current_user)):
    """Delete an expense."""
    user_id = current_user["id"]
    user_expenses = expenses_db.get(user_id, {})
    
    if expense_id not in user_expenses:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    del user_expenses[expense_id]
    return {"message": "Expense deleted successfully"}

# Category endpoints
@app.get("/api/v1/categories")
async def get_categories(current_user = Depends(get_current_user)):
    """Get all categories with expense summaries for current user."""
    user_id = current_user["id"]
    user_expenses = expenses_db.get(user_id, {}).values()
    category_summaries = []
    
    for category in categories:
        category_expenses = [exp for exp in user_expenses if exp["category"] == category]
        total_amount = sum(exp["amount"] for exp in category_expenses)
        
        category_summaries.append(CategoryResponse(
            name=category,
            total_expenses=total_amount,
            expense_count=len(category_expenses)
        ))
    
    return category_summaries

@app.get("/api/v1/summary")
async def get_summary(current_user = Depends(get_current_user)):
    """Get expense summary for current user."""
    user_id = current_user["id"]
    user_expenses = list(expenses_db.get(user_id, {}).values())
    
    total_expenses = len(user_expenses)
    total_amount = sum(exp["amount"] for exp in user_expenses)
    
    return {
        "total_expenses": total_expenses,
        "total_amount": total_amount,
        "categories_used": len(set(exp["category"] for exp in user_expenses)),
        "recent_expenses": user_expenses[-5:]  # Last 5 expenses
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)