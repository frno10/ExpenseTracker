"""Monitoring dashboard for visualizing metrics and alerts."""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..core.auth import get_current_user
from ..models.user import UserTable
from .health import health_checker
from .metrics import metrics_collector
from .alerts import alert_manager

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


class MonitoringDashboard:
    """Dashboard for monitoring system status."""
    
    @staticmethod
    async def get_system_overview() -> Dict[str, Any]:
        """Get system overview for dashboard."""
        # Get health status
        health_status = await health_checker.get_overall_health()
        
        # Get metrics summary
        metrics_summary = await metrics_collector.get_dashboard_metrics()
        
        # Get alert summary
        alert_summary = await alert_manager.get_alert_summary()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "health": health_status,
            "metrics": metrics_summary,
            "alerts": alert_summary,
            "status": "operational" if health_status["status"] == "healthy" else "degraded"
        }


@router.get("/health")
async def get_health_status():
    """Get system health status."""
    return await health_checker.get_overall_health()


@router.get("/health/{check_name}")
async def get_specific_health_check(check_name: str):
    """Get specific health check result."""
    result = await health_checker.run_check(check_name)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Health check '{check_name}' not found"
        )
    
    return {
        "name": result.name,
        "status": result.status.value,
        "response_time_ms": result.response_time_ms,
        "message": result.message,
        "details": result.details,
        "timestamp": result.timestamp.isoformat()
    }


@router.get("/metrics")
async def get_metrics_summary():
    """Get metrics summary."""
    return await metrics_collector.get_metrics_summary()


@router.get("/metrics/dashboard")
async def get_dashboard_metrics():
    """Get metrics formatted for dashboard."""
    return await metrics_collector.get_dashboard_metrics()


@router.get("/metrics/prometheus")
async def get_prometheus_metrics():
    """Get metrics in Prometheus format."""
    metrics_text = await metrics_collector.export_metrics_prometheus()
    return {"metrics": metrics_text}


@router.get("/alerts")
async def get_alerts_summary():
    """Get alerts summary."""
    return await alert_manager.get_alert_summary()


@router.get("/alerts/active")
async def get_active_alerts():
    """Get all active alerts."""
    alerts = alert_manager.get_active_alerts()
    return {
        "alerts": [
            {
                "id": alert.id,
                "rule_name": alert.rule_name,
                "severity": alert.severity.value,
                "status": alert.status.value,
                "message": alert.message,
                "metric_name": alert.metric_name,
                "metric_value": alert.metric_value,
                "threshold": alert.threshold,
                "started_at": alert.started_at.isoformat(),
                "labels": alert.labels
            }
            for alert in alerts
        ]
    }


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    current_user: UserTable = Depends(get_current_user)
):
    """Acknowledge an alert."""
    await alert_manager.acknowledge_alert(alert_id, str(current_user.id))
    return {"message": "Alert acknowledged"}


@router.get("/dashboard")
async def get_monitoring_dashboard():
    """Get complete monitoring dashboard data."""
    return await MonitoringDashboard.get_system_overview()


@router.get("/status")
async def get_system_status():
    """Get simple system status for external monitoring."""
    health = await health_checker.get_overall_health()
    return {
        "status": health["status"],
        "timestamp": health["timestamp"],
        "version": health["version"]
    }