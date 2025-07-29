"""
Comprehensive audit logging system for security and compliance.
"""
import logging
import json
from datetime import datetime
from typing import Any, Dict, Optional, List
from enum import Enum
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Column, String, DateTime, Text, Integer
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB

from app.core.database import Base

logger = logging.getLogger(__name__)


class AuditEventType(str, Enum):
    """Types of audit events."""
    
    # Authentication events
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"
    ACCOUNT_LOCKED = "account_locked"
    
    # Data access events
    DATA_READ = "data_read"
    DATA_CREATE = "data_create"
    DATA_UPDATE = "data_update"
    DATA_DELETE = "data_delete"
    DATA_EXPORT = "data_export"
    DATA_IMPORT = "data_import"
    
    # Security events
    SECURITY_VIOLATION = "security_violation"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    CSRF_VIOLATION = "csrf_violation"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    
    # System events
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    CONFIGURATION_CHANGE = "configuration_change"
    
    # Business events
    BUDGET_CREATED = "budget_created"
    BUDGET_UPDATED = "budget_updated"
    BUDGET_DELETED = "budget_deleted"
    BUDGET_EXCEEDED = "budget_exceeded"
    
    EXPENSE_CREATED = "expense_created"
    EXPENSE_UPDATED = "expense_updated"
    EXPENSE_DELETED = "expense_deleted"
    
    IMPORT_STARTED = "import_started"
    IMPORT_COMPLETED = "import_completed"
    IMPORT_FAILED = "import_failed"


class AuditSeverity(str, Enum):
    """Audit event severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuditLogTable(Base):
    """Database table for audit logs."""
    
    __tablename__ = "audit_logs"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    event_type = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), nullable=False, default=AuditSeverity.LOW)
    user_id = Column(PGUUID(as_uuid=True), nullable=True, index=True)
    session_id = Column(String(255), nullable=True, index=True)
    ip_address = Column(String(45), nullable=True, index=True)  # IPv6 compatible
    user_agent = Column(Text, nullable=True)
    resource_type = Column(String(50), nullable=True, index=True)
    resource_id = Column(String(255), nullable=True, index=True)
    action = Column(String(50), nullable=True)
    details = Column(JSONB, nullable=True)
    old_values = Column(JSONB, nullable=True)
    new_values = Column(JSONB, nullable=True)
    success = Column(Integer, nullable=False, default=1)  # 1 = success, 0 = failure
    error_message = Column(Text, nullable=True)


class AuditLogger:
    """
    Comprehensive audit logging system.
    """
    
    def __init__(self, db_session: Optional[AsyncSession] = None):
        """
        Initialize audit logger.
        
        Args:
            db_session: Database session for storing audit logs
        """
        self.db_session = db_session
        self.logger = logging.getLogger("audit")
    
    async def log_event(
        self,
        event_type: AuditEventType,
        severity: AuditSeverity = AuditSeverity.LOW,
        user_id: Optional[UUID] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        action: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> UUID:
        """
        Log an audit event.
        
        Args:
            event_type: Type of event
            severity: Event severity
            user_id: User ID associated with the event
            session_id: Session ID
            ip_address: Client IP address
            user_agent: Client user agent
            resource_type: Type of resource affected
            resource_id: ID of the resource affected
            action: Action performed
            details: Additional event details
            old_values: Previous values (for updates)
            new_values: New values (for updates)
            success: Whether the operation was successful
            error_message: Error message if operation failed
            
        Returns:
            Audit log entry ID
        """
        audit_id = uuid4()
        
        # Create audit log entry
        audit_entry = AuditLogTable(
            id=audit_id,
            timestamp=datetime.utcnow(),
            event_type=event_type.value,
            severity=severity.value,
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            details=details,
            old_values=old_values,
            new_values=new_values,
            success=1 if success else 0,
            error_message=error_message
        )
        
        # Store in database if session available
        if self.db_session:
            try:
                self.db_session.add(audit_entry)
                await self.db_session.commit()
            except Exception as e:
                logger.error(f"Failed to store audit log in database: {e}")
                await self.db_session.rollback()
        
        # Always log to application logger as well
        log_data = {
            "audit_id": str(audit_id),
            "event_type": event_type.value,
            "severity": severity.value,
            "user_id": str(user_id) if user_id else None,
            "session_id": session_id,
            "ip_address": ip_address,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "action": action,
            "success": success,
            "error_message": error_message,
            "details": details
        }
        
        # Log at appropriate level based on severity
        if severity == AuditSeverity.CRITICAL:
            self.logger.critical(f"AUDIT: {event_type.value}", extra=log_data)
        elif severity == AuditSeverity.HIGH:
            self.logger.error(f"AUDIT: {event_type.value}", extra=log_data)
        elif severity == AuditSeverity.MEDIUM:
            self.logger.warning(f"AUDIT: {event_type.value}", extra=log_data)
        else:
            self.logger.info(f"AUDIT: {event_type.value}", extra=log_data)
        
        return audit_id
    
    async def log_authentication_event(
        self,
        event_type: AuditEventType,
        user_id: Optional[UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> UUID:
        """
        Log authentication-related events.
        
        Args:
            event_type: Authentication event type
            user_id: User ID
            ip_address: Client IP address
            user_agent: Client user agent
            success: Whether authentication was successful
            error_message: Error message if failed
            details: Additional details
            
        Returns:
            Audit log entry ID
        """
        severity = AuditSeverity.HIGH if not success else AuditSeverity.MEDIUM
        
        return await self.log_event(
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            resource_type="authentication",
            success=success,
            error_message=error_message,
            details=details
        )
    
    async def log_data_access(
        self,
        action: str,
        resource_type: str,
        resource_id: str,
        user_id: UUID,
        ip_address: Optional[str] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> UUID:
        """
        Log data access events.
        
        Args:
            action: Action performed (create, read, update, delete)
            resource_type: Type of resource
            resource_id: Resource ID
            user_id: User performing the action
            ip_address: Client IP address
            old_values: Previous values (for updates)
            new_values: New values (for creates/updates)
            success: Whether operation was successful
            error_message: Error message if failed
            
        Returns:
            Audit log entry ID
        """
        event_type_map = {
            "create": AuditEventType.DATA_CREATE,
            "read": AuditEventType.DATA_READ,
            "update": AuditEventType.DATA_UPDATE,
            "delete": AuditEventType.DATA_DELETE,
            "export": AuditEventType.DATA_EXPORT,
            "import": AuditEventType.DATA_IMPORT
        }
        
        event_type = event_type_map.get(action.lower(), AuditEventType.DATA_READ)
        severity = AuditSeverity.MEDIUM if action.lower() in ["update", "delete"] else AuditSeverity.LOW
        
        return await self.log_event(
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            ip_address=ip_address,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            old_values=old_values,
            new_values=new_values,
            success=success,
            error_message=error_message
        )
    
    async def log_security_event(
        self,
        event_type: AuditEventType,
        severity: AuditSeverity,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        user_id: Optional[UUID] = None,
        details: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ) -> UUID:
        """
        Log security-related events.
        
        Args:
            event_type: Security event type
            severity: Event severity
            ip_address: Client IP address
            user_agent: Client user agent
            user_id: User ID if known
            details: Event details
            error_message: Error message
            
        Returns:
            Audit log entry ID
        """
        return await self.log_event(
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            resource_type="security",
            success=False,
            error_message=error_message,
            details=details
        )
    
    async def log_business_event(
        self,
        event_type: AuditEventType,
        user_id: UUID,
        resource_type: str,
        resource_id: str,
        action: str,
        details: Optional[Dict[str, Any]] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None
    ) -> UUID:
        """
        Log business logic events.
        
        Args:
            event_type: Business event type
            user_id: User performing the action
            resource_type: Type of resource
            resource_id: Resource ID
            action: Action performed
            details: Event details
            old_values: Previous values
            new_values: New values
            
        Returns:
            Audit log entry ID
        """
        return await self.log_event(
            event_type=event_type,
            severity=AuditSeverity.LOW,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            details=details,
            old_values=old_values,
            new_values=new_values,
            success=True
        )


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger(db_session: Optional[AsyncSession] = None) -> AuditLogger:
    """
    Get the global audit logger instance.
    
    Args:
        db_session: Database session for storing audit logs
        
    Returns:
        AuditLogger instance
    """
    global _audit_logger
    
    if _audit_logger is None or db_session:
        _audit_logger = AuditLogger(db_session)
    
    return _audit_logger


# Convenience functions for common audit events
async def audit_login_success(user_id: UUID, ip_address: str, user_agent: str, db_session: Optional[AsyncSession] = None):
    """Audit successful login."""
    logger = get_audit_logger(db_session)
    await logger.log_authentication_event(
        AuditEventType.LOGIN_SUCCESS,
        user_id=user_id,
        ip_address=ip_address,
        user_agent=user_agent,
        success=True
    )


async def audit_login_failure(ip_address: str, user_agent: str, error_message: str, db_session: Optional[AsyncSession] = None):
    """Audit failed login attempt."""
    logger = get_audit_logger(db_session)
    await logger.log_authentication_event(
        AuditEventType.LOGIN_FAILURE,
        ip_address=ip_address,
        user_agent=user_agent,
        success=False,
        error_message=error_message
    )


async def audit_data_change(
    action: str,
    resource_type: str,
    resource_id: str,
    user_id: UUID,
    old_values: Optional[Dict] = None,
    new_values: Optional[Dict] = None,
    db_session: Optional[AsyncSession] = None
):
    """Audit data changes."""
    logger = get_audit_logger(db_session)
    await logger.log_data_access(
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        user_id=user_id,
        old_values=old_values,
        new_values=new_values
    )


async def audit_security_violation(
    violation_type: str,
    ip_address: str,
    details: Dict[str, Any],
    severity: AuditSeverity = AuditSeverity.HIGH,
    db_session: Optional[AsyncSession] = None
):
    """Audit security violations."""
    logger = get_audit_logger(db_session)
    await logger.log_security_event(
        AuditEventType.SECURITY_VIOLATION,
        severity=severity,
        ip_address=ip_address,
        details={"violation_type": violation_type, **details}
    )