"""Security management API endpoints."""
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from ..core.database import get_db
from ..core.auth import get_current_user
from ..models.user import UserTable
from ..security.csrf import get_csrf_token
from ..security.session import session_manager, get_current_session
from ..security.audit import audit_logger, AuditEventType, AuditSeverity
from ..security.validation import InputValidator

router = APIRouter(prefix="/security", tags=["security"])


class CSRFTokenResponse(BaseModel):
    """CSRF token response model."""
    csrf_token: str


class SessionInfo(BaseModel):
    """Session information model."""
    session_id: str
    created_at: datetime
    last_activity: datetime
    ip_address: str
    user_agent: str
    is_current: bool


class SecuritySettingsResponse(BaseModel):
    """Security settings response model."""
    session_timeout_hours: int
    idle_timeout_hours: int
    max_sessions_per_user: int
    password_policy: dict
    two_factor_enabled: bool


class PasswordChangeRequest(BaseModel):
    """Password change request model."""
    current_password: str
    new_password: str
    confirm_password: str


@router.get("/csrf-token", response_model=CSRFTokenResponse)
async def get_csrf_token_endpoint(
    request: Request,
    csrf_token: str = Depends(get_csrf_token)
):
    """Get CSRF token for the current session."""
    return CSRFTokenResponse(csrf_token=csrf_token)


@router.get("/sessions", response_model=List[SessionInfo])
async def get_user_sessions(
    current_user: UserTable = Depends(get_current_user),
    current_session: dict = Depends(get_current_session)
):
    """Get all active sessions for the current user."""
    sessions = await session_manager.get_user_sessions(str(current_user.id))
    current_session_id = current_session.get("session_id") if current_session else None
    
    session_info = []
    for session in sessions:
        session_info.append(SessionInfo(
            session_id=session["session_id"],
            created_at=datetime.fromisoformat(session["created_at"]),
            last_activity=datetime.fromisoformat(session["last_activity"]),
            ip_address=session["ip_address"],
            user_agent=session["user_agent"],
            is_current=session["session_id"] == current_session_id
        ))
    
    return session_info


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserTable = Depends(get_current_user),
    current_session: dict = Depends(get_current_session)
):
    """Revoke a specific session."""
    # Validate session belongs to current user
    user_sessions = await session_manager.get_user_sessions(str(current_user.id))
    session_ids = [s["session_id"] for s in user_sessions]
    
    if session_id not in session_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Don't allow revoking current session
    current_session_id = current_session.get("session_id") if current_session else None
    if session_id == current_session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot revoke current session"
        )
    
    # Revoke session
    success = await session_manager.invalidate_session(session_id)
    
    if success:
        # Log security event
        await audit_logger.log_event(
            db=db,
            event_type=AuditEventType.LOGOUT,
            severity=AuditSeverity.MEDIUM,
            user_id=str(current_user.id),
            action="session_revoked",
            details={"revoked_session_id": session_id},
            success=True
        )
        
        return {"message": "Session revoked successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke session"
        )


@router.delete("/sessions")
async def revoke_all_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: UserTable = Depends(get_current_user),
    current_session: dict = Depends(get_current_session)
):
    """Revoke all sessions except the current one."""
    current_session_id = current_session.get("session_id") if current_session else None
    
    revoked_count = await session_manager.invalidate_user_sessions(
        str(current_user.id),
        except_session=current_session_id
    )
    
    # Log security event
    await audit_logger.log_event(
        db=db,
        event_type=AuditEventType.LOGOUT,
        severity=AuditSeverity.MEDIUM,
        user_id=str(current_user.id),
        action="all_sessions_revoked",
        details={"revoked_count": revoked_count},
        success=True
    )
    
    return {"message": f"Revoked {revoked_count} sessions"}


@router.get("/settings", response_model=SecuritySettingsResponse)
async def get_security_settings(
    current_user: UserTable = Depends(get_current_user)
):
    """Get security settings for the current user."""
    return SecuritySettingsResponse(
        session_timeout_hours=24,
        idle_timeout_hours=2,
        max_sessions_per_user=5,
        password_policy={
            "min_length": 8,
            "require_uppercase": True,
            "require_lowercase": True,
            "require_numbers": True,
            "require_special_chars": True,
            "max_age_days": 90
        },
        two_factor_enabled=getattr(current_user, 'two_factor_enabled', False)
    )


@router.post("/change-password")
async def change_password(
    request: PasswordChangeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserTable = Depends(get_current_user)
):
    """Change user password."""
    from ..security.encryption import verify_password, hash_password
    from ..repositories.user import user_repository
    
    # Verify current password
    if not verify_password(request.current_password, current_user.password_hash):
        # Log failed attempt
        await audit_logger.log_event(
            db=db,
            event_type=AuditEventType.PASSWORD_CHANGE,
            severity=AuditSeverity.HIGH,
            user_id=str(current_user.id),
            action="password_change_failed",
            details={"reason": "invalid_current_password"},
            success=False
        )
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Validate new password
    if request.new_password != request.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password and confirmation do not match"
        )
    
    # Validate password strength
    if len(request.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )
    
    # Hash new password
    new_password_hash = hash_password(request.new_password)
    
    # Update password
    await user_repository.update(
        db,
        str(current_user.id),
        {"password_hash": new_password_hash}
    )
    
    # Invalidate all other sessions
    await session_manager.invalidate_user_sessions(str(current_user.id))
    
    # Log successful password change
    await audit_logger.log_event(
        db=db,
        event_type=AuditEventType.PASSWORD_CHANGE,
        severity=AuditSeverity.MEDIUM,
        user_id=str(current_user.id),
        action="password_changed",
        success=True
    )
    
    return {"message": "Password changed successfully"}


@router.get("/audit-log")
async def get_audit_log(
    limit: int = 50,
    offset: int = 0,
    event_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: UserTable = Depends(get_current_user)
):
    """Get audit log entries for the current user."""
    from sqlalchemy import select, desc
    from ..security.audit import AuditLogEntry
    
    # Build query
    query = select(AuditLogEntry).where(
        AuditLogEntry.user_id == current_user.id
    )
    
    if event_type:
        query = query.where(AuditLogEntry.event_type == event_type)
    
    query = query.order_by(desc(AuditLogEntry.timestamp)).limit(limit).offset(offset)
    
    # Execute query
    result = await db.execute(query)
    audit_entries = result.scalars().all()
    
    # Convert to response format
    entries = []
    for entry in audit_entries:
        entries.append({
            "id": str(entry.id),
            "timestamp": entry.timestamp,
            "event_type": entry.event_type,
            "severity": entry.severity,
            "ip_address": entry.ip_address,
            "user_agent": entry.user_agent,
            "resource": entry.resource,
            "action": entry.action,
            "success": bool(entry.success),
            "details": entry.details
        })
    
    return {
        "entries": entries,
        "total": len(entries),
        "limit": limit,
        "offset": offset
    }


@router.post("/validate-input")
async def validate_input_endpoint(
    data: dict,
    current_user: UserTable = Depends(get_current_user)
):
    """Validate input data using security validators."""
    from ..security.validation import sanitize_input
    
    try:
        # Sanitize input
        sanitized_data = sanitize_input(data)
        
        # Perform additional validation based on data type
        validation_results = {}
        
        for key, value in sanitized_data.items():
            if key == "email" and value:
                validation_results[key] = {
                    "valid": InputValidator.validate_email(str(value)),
                    "sanitized_value": value
                }
            elif key == "amount" and value:
                try:
                    validated_amount = InputValidator.validate_amount(value)
                    validation_results[key] = {
                        "valid": True,
                        "sanitized_value": str(validated_amount)
                    }
                except ValueError as e:
                    validation_results[key] = {
                        "valid": False,
                        "error": str(e),
                        "sanitized_value": value
                    }
            else:
                validation_results[key] = {
                    "valid": True,
                    "sanitized_value": value
                }
        
        return {
            "original_data": data,
            "sanitized_data": sanitized_data,
            "validation_results": validation_results
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation failed: {str(e)}"
        )