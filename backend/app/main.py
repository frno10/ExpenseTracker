"""
Expense Tracker - FastAPI application with Supabase authentication.

Architecture:
- Auth (register/login): Supabase Auth API
- Expense CRUD & statement import: Supabase REST API (inline routes)
- Budgets, analytics, recurring expenses, etc.: Modular routers with SQLAlchemy
"""
import logging
import os
import sys
import tempfile
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import Client, create_client

from app.core.auth import CurrentUser, get_current_user
from app.core.config import settings

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Supabase client
# ---------------------------------------------------------------------------
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase: Optional[Client] = None

if supabase_url and supabase_key:
    try:
        supabase = create_client(supabase_url, supabase_key)
        logger.info("Supabase client created successfully")
    except Exception as e:
        logger.error(f"Failed to create Supabase client: {e}")
else:
    logger.warning("Supabase client not initialized - missing SUPABASE_URL or SUPABASE_KEY")


# ---------------------------------------------------------------------------
# Application lifespan - initialize and close database
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup, close on shutdown."""
    if settings.database_mode == "postgresql":
        try:
            from app.core.database import close_db, init_db, initialize_database

            await initialize_database()
            logger.info("Database connection initialized")
            await init_db()
            logger.info("Database tables initialized")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            # Don't crash - inline routes using Supabase REST still work
    yield
    if settings.database_mode == "postgresql":
        try:
            from app.core.database import close_db

            await close_db()
            logger.info("Database connections closed")
        except Exception:
            pass


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Expense Tracker API",
    description="Personal finance management system",
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://*.netlify.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# Request logging middleware (no sensitive data)
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    logger.info(f"{request.method} {request.url.path} -> {response.status_code} ({duration:.3f}s)")
    return response


# ---------------------------------------------------------------------------
# Include modular API routers
# ---------------------------------------------------------------------------
try:
    from app.api.monitoring import router as monitoring_router

    app.include_router(monitoring_router, prefix="/api/v1/monitoring", tags=["monitoring"])
except ImportError as e:
    logger.warning(f"Could not load monitoring router: {e}")

try:
    from app.api.budgets import router as budgets_router

    app.include_router(budgets_router)
    logger.info("Budgets router loaded")
except ImportError as e:
    logger.warning(f"Could not load budgets router: {e}")

try:
    from app.api.analytics import router as analytics_router

    app.include_router(analytics_router)
    logger.info("Analytics router loaded")
except ImportError as e:
    logger.warning(f"Could not load analytics router: {e}")

try:
    from app.api.recurring_expenses import router as recurring_expenses_router

    app.include_router(recurring_expenses_router, prefix="/api")
    logger.info("Recurring expenses router loaded")
except ImportError as e:
    logger.warning(f"Could not load recurring expenses router: {e}")

try:
    from app.api.export import router as export_router

    app.include_router(export_router, prefix="/api")
    logger.info("Export router loaded")
except ImportError as e:
    logger.warning(f"Could not load export router: {e}")

try:
    from app.api.accounts import router as accounts_router

    app.include_router(accounts_router, prefix="/api")
    logger.info("Accounts router loaded")
except ImportError as e:
    logger.warning(f"Could not load accounts router: {e}")

try:
    from app.api.attachments import router as attachments_router

    app.include_router(attachments_router, prefix="/api")
    logger.info("Attachments router loaded")
except ImportError as e:
    logger.warning(f"Could not load attachments router: {e}")

try:
    from app.api.websocket import router as websocket_router

    app.include_router(websocket_router, prefix="/api")
    logger.info("WebSocket router loaded")
except ImportError as e:
    logger.warning(f"Could not load websocket router: {e}")

try:
    from app.api.security import router as security_router

    app.include_router(security_router, prefix="/api")
    logger.info("Security router loaded")
except ImportError as e:
    logger.warning(f"Could not load security router: {e}")


# ---------------------------------------------------------------------------
# Pydantic models for inline routes
# ---------------------------------------------------------------------------
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


# Default categories
categories = ["Food", "Transportation", "Entertainment", "Utilities", "Healthcare", "Shopping", "Other"]


# ---------------------------------------------------------------------------
# Health & root
# ---------------------------------------------------------------------------
@app.get("/")
async def root():
    return {"message": "Expense Tracker API is running!"}


@app.get("/health")
async def health_check():
    try:
        from app.monitoring.health import health_checker

        db_result = await health_checker.run_check("database")
        status_value = db_result.status.value
        if status_value == "healthy":
            return {"status": "healthy", "message": "API is operational"}
        elif status_value == "degraded":
            return {"status": "degraded", "message": "API is operational but degraded"}
        return {"status": "unhealthy", "message": "API has health issues"}
    except Exception:
        return {"status": "healthy", "message": "API is running"}


# ---------------------------------------------------------------------------
# Auth routes (Supabase Auth)
# ---------------------------------------------------------------------------
@app.post("/api/v1/auth/register", response_model=AuthResponse)
async def register(user_data: UserRegister):
    """Register a new user via Supabase Auth."""
    if supabase is None:
        raise HTTPException(status_code=500, detail="Registration service unavailable")

    try:
        response = supabase.auth.sign_up({
            "email": user_data.email,
            "password": user_data.password,
            "options": {"data": {"full_name": user_data.full_name}},
        })

        if response.user:
            return AuthResponse(
                user=UserResponse(
                    id=response.user.id,
                    email=response.user.email,
                    full_name=user_data.full_name,
                    created_at=datetime.now().isoformat(),
                ),
                access_token=response.session.access_token if response.session else "",
            )
        raise HTTPException(status_code=400, detail="Registration failed - no user created")

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e).lower()
        if "already registered" in error_msg or "already been registered" in error_msg:
            raise HTTPException(status_code=400, detail="An account with this email already exists.")
        raise HTTPException(status_code=400, detail=f"Registration failed: {str(e)}")


@app.post("/api/v1/auth/login", response_model=AuthResponse)
async def login(user_data: UserLogin):
    """Login via Supabase Auth."""
    if supabase is None:
        raise HTTPException(status_code=500, detail="Login service unavailable")

    try:
        response = supabase.auth.sign_in_with_password({
            "email": user_data.email,
            "password": user_data.password,
        })

        if response.user and response.session:
            return AuthResponse(
                user=UserResponse(
                    id=response.user.id,
                    email=response.user.email,
                    full_name=(response.user.user_metadata or {}).get("full_name"),
                    created_at=response.user.created_at,
                ),
                access_token=response.session.access_token,
            )
        elif response.user and not response.session:
            if not getattr(response.user, "email_confirmed_at", None):
                raise HTTPException(
                    status_code=403,
                    detail="Please check your email and confirm your account before logging in.",
                )
            raise HTTPException(status_code=401, detail="Authentication failed. Please try again.")
        else:
            raise HTTPException(status_code=401, detail="Invalid email or password.")

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e).lower()
        if "email not confirmed" in error_msg or "email_not_confirmed" in error_msg:
            raise HTTPException(status_code=403, detail="Please check your email and confirm your account.")
        if "invalid login credentials" in error_msg or "invalid_credentials" in error_msg:
            raise HTTPException(status_code=401, detail="Invalid email or password.")
        if "user not found" in error_msg:
            raise HTTPException(status_code=404, detail="No account found with this email. Please register first.")
        if "too many requests" in error_msg or "rate_limit" in error_msg:
            raise HTTPException(status_code=429, detail="Too many login attempts. Please wait and try again.")
        raise HTTPException(status_code=401, detail="Login failed. Please check your credentials.")


@app.post("/api/v1/auth/resend-confirmation")
async def resend_confirmation(request: ResendConfirmationRequest):
    """Resend email confirmation."""
    try:
        supabase.auth.resend({"type": "signup", "email": request.email})
        return {"message": "Confirmation email sent. Please check your inbox and spam folder.", "email": request.email}
    except Exception:
        raise HTTPException(status_code=400, detail="Failed to resend confirmation email.")


@app.get("/api/v1/auth/me", response_model=UserResponse)
async def get_me(current_user: CurrentUser = Depends(get_current_user)):
    """Get current user info."""
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=None,
        created_at=datetime.now().isoformat(),
    )


# ---------------------------------------------------------------------------
# Expense CRUD (Supabase REST)
# ---------------------------------------------------------------------------
@app.post("/api/v1/expenses", response_model=ExpenseResponse)
async def create_expense(expense: ExpenseCreate, current_user: CurrentUser = Depends(get_current_user)):
    """Create a new expense."""
    user_id = str(current_user.id)
    expense_data = {
        "user_id": user_id,
        "amount": expense.amount,
        "description": expense.description,
        "category": expense.category,
        "date": expense.date or datetime.now().strftime("%Y-%m-%d"),
    }
    try:
        result = supabase.table("expenses").insert(expense_data).execute()
        if result.data:
            return ExpenseResponse(**result.data[0])
        raise HTTPException(status_code=500, detail="Failed to create expense")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating expense: {e}")
        raise HTTPException(status_code=500, detail="Failed to create expense")


@app.get("/api/v1/expenses")
async def get_expenses(current_user: CurrentUser = Depends(get_current_user)):
    """Get all expenses for current user."""
    try:
        result = supabase.table("expenses").select("*").eq("user_id", str(current_user.id)).execute()
        return result.data or []
    except Exception as e:
        logger.error(f"Error fetching expenses: {e}")
        return []


@app.get("/api/v1/expenses/{expense_id}", response_model=ExpenseResponse)
async def get_expense(expense_id: str, current_user: CurrentUser = Depends(get_current_user)):
    """Get a specific expense."""
    try:
        result = (
            supabase.table("expenses")
            .select("*")
            .eq("id", expense_id)
            .eq("user_id", str(current_user.id))
            .execute()
        )
        if result.data:
            return ExpenseResponse(**result.data[0])
        raise HTTPException(status_code=404, detail="Expense not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching expense: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch expense")


@app.put("/api/v1/expenses/{expense_id}", response_model=ExpenseResponse)
async def update_expense(
    expense_id: str,
    expense: ExpenseCreate,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Update an expense."""
    user_id = str(current_user.id)
    try:
        existing = supabase.table("expenses").select("*").eq("id", expense_id).eq("user_id", user_id).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Expense not found")

        update_data = {
            "amount": expense.amount,
            "description": expense.description,
            "category": expense.category,
            "date": expense.date or existing.data[0]["date"],
        }
        result = supabase.table("expenses").update(update_data).eq("id", expense_id).eq("user_id", user_id).execute()
        if result.data:
            return ExpenseResponse(**result.data[0])
        raise HTTPException(status_code=500, detail="Failed to update expense")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating expense: {e}")
        raise HTTPException(status_code=500, detail="Failed to update expense")


@app.delete("/api/v1/expenses/{expense_id}")
async def delete_expense(expense_id: str, current_user: CurrentUser = Depends(get_current_user)):
    """Delete an expense."""
    user_id = str(current_user.id)
    try:
        existing = supabase.table("expenses").select("id").eq("id", expense_id).eq("user_id", user_id).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Expense not found")
        supabase.table("expenses").delete().eq("id", expense_id).eq("user_id", user_id).execute()
        return {"message": "Expense deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting expense: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete expense")


# ---------------------------------------------------------------------------
# Categories & Summary (Supabase REST)
# ---------------------------------------------------------------------------
@app.get("/api/v1/categories")
async def get_categories(current_user: CurrentUser = Depends(get_current_user)):
    """Get all categories with expense summaries."""
    try:
        result = supabase.table("expenses").select("*").eq("user_id", str(current_user.id)).execute()
        user_expenses = result.data or []

        return [
            CategoryResponse(
                name=cat,
                total_expenses=sum(float(e["amount"]) for e in user_expenses if e["category"] == cat),
                expense_count=sum(1 for e in user_expenses if e["category"] == cat),
            )
            for cat in categories
        ]
    except Exception as e:
        logger.error(f"Error fetching categories: {e}")
        return []


@app.get("/api/v1/summary")
async def get_summary(current_user: CurrentUser = Depends(get_current_user)):
    """Get expense summary for current user."""
    try:
        result = (
            supabase.table("expenses")
            .select("*")
            .eq("user_id", str(current_user.id))
            .order("created_at", desc=True)
            .execute()
        )
        user_expenses = result.data or []
        return {
            "total_expenses": len(user_expenses),
            "total_amount": sum(float(e["amount"]) for e in user_expenses),
            "categories_used": len({e["category"] for e in user_expenses}),
            "recent_expenses": user_expenses[:5],
        }
    except Exception as e:
        logger.error(f"Error fetching summary: {e}")
        return {"total_expenses": 0, "total_amount": 0, "categories_used": 0, "recent_expenses": []}


# ---------------------------------------------------------------------------
# Statement Import (inline, Supabase REST)
# ---------------------------------------------------------------------------
uploaded_files: Dict[str, Dict[str, Any]] = {}
parse_results: Dict[str, Dict[str, Any]] = {}


@app.post("/api/statement-import/upload")
async def upload_statement(
    file: UploadFile = File(...),
    bank_hint: Optional[str] = Form(None),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Upload a statement file for processing."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    if file.size and file.size > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds 50MB limit")

    ext = file.filename.rsplit(".", 1)[-1].lower()
    supported = ["pdf", "csv", "xlsx", "xls", "ofx", "qif", "txt"]
    if ext not in supported:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {ext}. Supported: {', '.join(supported)}")

    upload_id = str(uuid.uuid4())
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}")
    content = await file.read()
    temp_file.write(content)
    temp_file.close()

    uploaded_files[upload_id] = {
        "user_id": str(current_user.id),
        "filename": file.filename,
        "file_size": len(content),
        "file_path": temp_file.name,
        "file_type": ext,
        "bank_hint": bank_hint,
        "upload_time": datetime.now().isoformat(),
    }

    parser_map = {
        "pdf": "pdf_parser", "csv": "csv_parser", "txt": "csv_parser",
        "xlsx": "excel_parser", "xls": "excel_parser",
        "ofx": "ofx_parser", "qfx": "ofx_parser", "qif": "qif_parser",
    }
    return {
        "upload_id": upload_id, "filename": file.filename, "file_size": len(content),
        "file_type": ext, "supported_format": True,
        "detected_parser": parser_map.get(ext), "validation_errors": [],
    }


@app.post("/api/statement-import/preview/{upload_id}")
async def preview_statement(upload_id: str, current_user: CurrentUser = Depends(get_current_user)):
    """Preview parsed transactions from uploaded statement."""
    if upload_id not in uploaded_files:
        raise HTTPException(status_code=404, detail="Upload not found")

    info = uploaded_files[upload_id]
    if info["user_id"] != str(current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")

    if info["file_type"] == "pdf":
        from app.parsers.config import config_manager
        from app.parsers.pdf_parser import PDFParser

        parser = PDFParser()
        if info.get("bank_hint") and "csob" in info["bank_hint"].lower():
            csob_config = config_manager.load_bank_config("csob_slovakia")
            if csob_config and "pdf_config" in csob_config:
                parser.config.settings.update(csob_config["pdf_config"])

        result = await parser.parse(info["file_path"])
        sample = [
            {
                "index": i, "date": tx.date.isoformat(), "description": tx.description,
                "amount": float(tx.amount), "merchant": tx.merchant, "category": tx.category,
                "account": tx.account or "Unknown", "reference": tx.reference or "",
            }
            for i, tx in enumerate(result.transactions[:10])
        ]
        parse_results[upload_id] = {
            "success": result.success, "transactions": result.transactions,
            "errors": result.errors, "warnings": result.warnings, "metadata": result.metadata,
        }
        return {
            "upload_id": upload_id, "success": result.success,
            "transaction_count": len(result.transactions), "sample_transactions": sample,
            "errors": result.errors, "warnings": result.warnings, "metadata": result.metadata,
        }

    return {
        "upload_id": upload_id, "success": False, "transaction_count": 0,
        "sample_transactions": [],
        "errors": [f"File type '{info['file_type']}' is not yet supported for parsing"],
        "warnings": [], "metadata": {"file_type": info["file_type"]},
    }


@app.post("/api/statement-import/analyze-duplicates/{upload_id}")
async def analyze_duplicates(upload_id: str, current_user: CurrentUser = Depends(get_current_user)):
    """Analyze transactions for potential duplicates."""
    if upload_id not in parse_results:
        raise HTTPException(status_code=404, detail="Parse result not found. Please preview first.")

    pr = parse_results[upload_id]
    user_id = str(current_user.id)
    try:
        result = supabase.table("expenses").select("*").eq("user_id", user_id).execute()
        user_expenses = result.data or []
    except Exception:
        user_expenses = []

    analysis = []
    for i, tx in enumerate(pr["transactions"]):
        potential_duplicates = []
        is_dup = False
        for exp in user_expenses:
            date_match = exp.get("date") == tx.date.isoformat()[:10]
            amount_match = abs(float(exp.get("amount", 0)) - float(tx.amount)) < 0.01
            if date_match and amount_match:
                is_dup = True
                potential_duplicates.append({
                    "expense_id": exp.get("id"), "match_score": 0.9,
                    "match_reasons": ["date_match", "amount_match"],
                })
            elif tx.description.lower() in exp.get("description", "").lower() and amount_match:
                potential_duplicates.append({
                    "expense_id": exp.get("id"), "match_score": 0.7,
                    "match_reasons": ["description_similarity", "amount_match"],
                })

        analysis.append({
            "transaction_index": i,
            "transaction": {
                "date": tx.date.isoformat(), "description": tx.description,
                "amount": float(tx.amount), "merchant": tx.merchant,
            },
            "is_likely_duplicate": is_dup,
            "confidence_score": 0.9 if is_dup else 0.1,
            "potential_duplicates": potential_duplicates,
        })

    return {
        "upload_id": upload_id,
        "total_transactions": len(analysis),
        "likely_duplicates": sum(1 for a in analysis if a["is_likely_duplicate"]),
        "analysis": analysis,
    }


@app.post("/api/statement-import/confirm/{upload_id}")
async def confirm_import(
    upload_id: str, request: dict, current_user: CurrentUser = Depends(get_current_user),
):
    """Confirm and execute the statement import."""
    if upload_id not in parse_results:
        raise HTTPException(status_code=404, detail="Parse result not found")

    pr = parse_results[upload_id]
    selected = request.get("selected_transactions", list(range(len(pr["transactions"]))))
    user_id = str(current_user.id)
    imported = 0
    skipped = 0
    errors = []

    for i in selected:
        if i >= len(pr["transactions"]):
            continue
        tx = pr["transactions"][i]
        try:
            result = supabase.table("expenses").insert({
                "user_id": user_id, "description": tx.description,
                "amount": float(tx.amount), "category": tx.category or "Other",
                "date": tx.date.isoformat()[:10],
            }).execute()
            if result.data:
                imported += 1
            else:
                skipped += 1
                errors.append(f"Failed to save transaction {i}")
        except Exception as e:
            skipped += 1
            errors.append(f"Failed to import transaction {i}: {str(e)}")

    # Cleanup
    info = uploaded_files.pop(upload_id, None)
    parse_results.pop(upload_id, None)
    if info and os.path.exists(info["file_path"]):
        try:
            os.unlink(info["file_path"])
        except OSError:
            pass

    return {
        "import_id": str(uuid.uuid4()), "success": imported > 0,
        "imported_count": imported, "skipped_count": skipped,
        "duplicate_count": 0, "errors": errors,
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
