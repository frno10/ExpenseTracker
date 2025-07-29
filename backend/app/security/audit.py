"""Audit logging for security events."""
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Column, String, DateTime, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from uuid import uuid4

from ..core.database import Base
from ..core.config import settings


class AuditEventType(str, Enum):
    """Types of audit events."""
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    PASSWORD_CHANGE = "password_change"
    ACCOUNT_LOCKED = "account_locked"
    PERMISSION_DENIED = "permission_denied"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    DATA_DELETION = "data_deletion"
    EXPORT = "export"
    IMPORT = "import"
    CONFIGURATION_CHANGE = "configuration_change"
    SECURITY_VIOLATION = "security_violation"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"


class AuditSeverity(str, Enum):
    """Severity levels for audit events."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuditLogEntry(Base):
    """Database model for audit log entries."""
    
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    event_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    session_id = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    resource = Column(String(255), nullable=True)
    action = Column(String(100), nullable=True)
    details = Column(Text, nullable=True)
    success = Column(Integer, nullable=False, default=1)  # 1 for success, 0 for failure


class AuditLogger:
    """Audit logging service."""
    
    def __init__(self):
        self.logger = logging.getLogger("audit")
        self._setup_logger()
    
    def _setup_logger(self):
        """Set up audit logger configuration."""
        if not self.logger.handlers:
            # Create file handler for audit logs
            handler = logging.FileHandler(
                filename=f"{settings.LOG_DIR}/audit.log",
                mode='a',
                encoding='utf-8'
            )
            
            # Create formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    async def log_event(
        self,
        db: AsyncSession,
        event_type: AuditEventType,
        severity: AuditSeverity = AuditSeverity.LOW,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        success: bool = True
    ) -> None:
        """Log an audit event."""
        
        # Create audit log entry
        audit_entry = AuditLogEntry(
            event_type=event_type.value,
            severity=severity.value,
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            resource=resource,
            action=action,
            details=json.dumps(details) if details else None,
            success=1 if success else 0
        )
        
        # Save to database
        try:
            db.add(audit_entry)
            await db.commit()
        except Exception as e:
            await db.rollback()
            self.logger.error(f"Failed to save audit log to database: {e}")
        
        # Also log to file
        log_message = self._format_log_message(
            event_type, severity, user_id, session_id, ip_address,
            resource, action, details, success
        )
        
        if severity in [AuditSeverity.HIGH, AuditSeverity.CRITICAL]:
            self.logger.error(log_message)
        elif severity == AuditSeverity.MEDIUM:
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)
    
    def _format_log_message(
        self,
        event_type: AuditEventType,
        severity: AuditSeverity,
        user_id: Optional[str],
        session_id: Optional[str],
        ip_address: Optional[str],
        resource: Optional[str],
        action: Optional[str],
        details: Optional[Dict[str, Any]],
        success: bool
    ) -> str:
        """Format audit log message."""
        parts = [
            f"EVENT={event_type.value}",
            f"SEVERITY={severity.value}",
            f"SUCCESS={'YES' if success else 'NO'}"
        ]
        
        if user_id:
            parts.append(f"USER_ID={user_id}")
        if session_id:
            parts.append(f"SESSION_ID={session_id}")
        if ip_address:
            parts.append(f"IP={ip_address}")
        if resource:
            parts.append(f"RESOURCE={resource}")
        if action:
            parts.append(f"ACTION={action}")
        if details:
            parts.append(f"DETAILS={json.dumps(details)}")
        
        return " | ".join(parts)
    
    async def log_login_attempt(
        self,
        db: AsyncSession,
        user_id: Optional[str],
        ip_address: str,
        user_agent: str,
        success: bool,
        failure_reason: Optional[str] = None
    ) -> None:
        """Log login attempt."""
        details = {}
        if failure_reason:
            details["failure_reason"] = failure_reason
        
        await self.log_event(
            db=db,
            event_type=AuditEventType.LOGIN if success else AuditEventType.LOGIN_FAILED,
            severity=AuditSeverity.LOW if success else AuditSeverity.MEDIUM,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            action="login",
            details=details,
            success=success
        )
    
    async def log_data_access(
        self,
        db: AsyncSession,
        user_id: str,
        resource: str,
        action: str,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log data access event."""
        await self.log_event(
            db=db,
            event_type=AuditEventType.DATA_ACCESS,
            severity=AuditSeverity.LOW,
            user_id=user_id,
            ip_address=ip_address,
            resource=resource,
            action=action,
            details=details
        )
    
    async def log_data_modification(
        self,
        db: AsyncSession,
        user_id: str,
        resource: str,
        action: str,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log data modification event."""
        await self.log_event(
            db=db,
            event_type=AuditEventType.DATA_MODIFICATION,
            severity=AuditSeverity.MEDIUM,
            user_id=user_id,
            ip_address=ip_address,
            resource=resource,
            action=action,
            details=details
        )
    
    async def log_security_violation(
        self,
        db: AsyncSession,
        event_description: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log security violation."""
        await self.log_event(
            db=db,
            event_type=AuditEventType.SECURITY_VIOLATION,
            severity=AuditSeverity.HIGH,
            user_id=user_id,
            ip_address=ip_address,
            action="security_violation",
            details={
                "description": event_description,
                **(details or {})
            },
            success=False
        )
    
    async def log_export_event(
        self,
        db: AsyncSession,
        user_id: str,
        export_type: str,
        record_count: int,
        ip_address: Optional[str] = None
    ) -> None:
        """Log data export event."""
        await self.log_event(
            db=db,
            event_type=AuditEventType.EXPORT,
            severity=AuditSeverity.MEDIUM,
            user_id=user_id,
            ip_address=ip_address,
            resource="data_export",
            action="export",
            details={
                "export_type": export_type,
                "record_count": record_count
            }
        )


# Global audit logger instance
audit_logger = AuditLogger()


# Decorator for auditing function calls
def audit_action(
    event_type: AuditEventType,
    severity: AuditSeverity = AuditSeverity.LOW,
    resource: Optional[str] = None
):
    """Decorator to audit function calls."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract common parameters
            db = kwargs.get('db') or (args[0] if args else None)
            user_id = kwargs.get('user_id')
            
            try:
                result = await func(*args, **kwargs)
                
                # Log successful action
                if db and hasattr(db, 'add'):  # Check if it's a database session
                    await audit_logger.log_event(
                        db=db,
                        event_type=event_type,
                        severity=severity,
                        user_id=user_id,
                        resource=resource or func.__name__,
                        action=func.__name__,
                        success=True
                    )
                
                return result
                
            except Exception as e:
                # Log failed action
                if db and hasattr(db, 'add'):
                    await audit_logger.log_event(
                        db=db,
                        event_type=event_type,
                        severity=AuditSeverity.HIGH,
                        user_id=user_id,
                        resource=resource or func.__name__,
                        action=func.__name__,
                        details={"error": str(e)},
                        success=False
                    )
                
                raise
        
        return wrapper
    return decorator