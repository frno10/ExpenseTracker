"""Monitoring and alerting API endpoints."""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from ..core.auth import get_current_user, require_admin
from ..models.user import UserTable
from ..monitoring.health import health_checker, HealthStatus
from ..monitoring.metrics import metrics_collector
from ..monitoring.alerts import alert_manager, AlertSeverity, AlertStatus
from ..monitoring.dashboard import MonitoringDashboard, DashboardTimeRange

router = APIRouter(prefix="/monitoring", tags=["monitoring"])

# Initialize dashboard
dashboard = MonitoringDashboard(health_checker, metrics_collector, alert_manager)


class HealthCheckResponse(BaseModel):
    """Health check response model."""
    name: str
    status: str
    message: str
    response_time_ms: float
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None


class SystemHealthResponse(BaseModel):
    """System health response model."""
    overall_status: str
    overall_message: str
    response_time_ms: float
    last_updated: datetime
    checks: Dict[str, HealthCheckResponse]
    summary: Dict[str, int]


class MetricResponse(BaseModel):
    """Metric response model."""
    name: str
    type: str
    description: str
    unit: str
    current_value: Optional[float]
    last_updated: Optional[datetime]
    labels: Dict[str, str]


class AlertResponse(BaseModel):
    """Alert response model."""
    id: str
    name: str
    description: str
    severity: str
    status: str
    created_at: datetime
    updated_at: datetime
    source: str
    labels: Dict[str, str]
    resolved_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None


class DashboardResponse(BaseModel):
    """Dashboard response model."""
    system_health: Dict[str, Any]
    key_metrics: Dict[str, Any]
    active_alerts: List[Dict[str, Any]]
    charts: Dict[str, List[Dict[str, Any]]]
    summary: Dict[str, Any]


@router.get("/health", response_model=SystemHealthResponse)
async def get_system_health():
    """Get overall system health status."""
    overall_health = await health_checker.get_overall_health()
    individual_checks = await health_checker.run_all_checks()
    
    return SystemHealthResponse(
        overall_status=overall_health.status.value,
        overall_message=overall_health.message,
        response_time_ms=overall_health.response_time_ms,
        last_updated=overall_health.timestamp,
        checks={
            name: HealthCheckResponse(
                name=result.name,
                status=result.status.value,
                message=result.message,
                response_time_ms=result.response_time_ms,
                timestamp=result.timestamp,
                details=result.details
            )
            for name, result in individual_checks.items()
        },
        summary=overall_health.details.get("summary", {}) if overall_health.details else {}
    )


@router.get("/health/{check_name}", response_model=HealthCheckResponse)
async def get_health_check(check_name: str):
    """Get specific health check status."""
    result = await health_checker.run_check(check_name)
    
    return HealthCheckResponse(
        name=result.name,
        status=result.status.value,
        message=result.message,
        response_time_ms=result.response_time_ms,
        timestamp=result.timestamp,
        details=result.details
    )


@router.get("/metrics", response_model=List[MetricResponse])
async def get_all_metrics(
    current_user: UserTable = Depends(require_admin)
):
    """Get all metrics (admin only)."""
    all_metrics = metrics_collector.get_all_metrics()
    
    return [
        MetricResponse(
            name=metric_data["name"],
            type=metric_data["type"],
            description=metric_data["description"],
            unit=metric_data["unit"],
            current_value=metric_data["current_value"],
            last_updated=datetime.fromisoformat(metric_data["last_updated"]) if metric_data["last_updated"] else None,
            labels=metric_data["labels"]
        )
        for metric_data in all_metrics.values()
    ]


@router.get("/metrics/{metric_name}")
async def get_metric(
    metric_name: str,
    time_range_hours: int = Query(24, ge=1, le=168),  # 1 hour to 1 week
    current_user: UserTable = Depends(require_admin)
):
    """Get specific metric data with time range."""
    metric = metrics_collector.get_metric(metric_name)
    
    if not metric:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Metric '{metric_name}' not found"
        )
    
    time_range = timedelta(hours=time_range_hours)
    values = metrics_collector.get_metric_value(metric_name, time_range)
    
    return {
        "name": metric.name,
        "type": metric.type.value,
        "description": metric.description,
        "unit": metric.unit,
        "labels": metric.labels,
        "values": [
            {
                "value": v.value,
                "timestamp": v.timestamp.isoformat(),
                "labels": v.labels
            }
            for v in values
        ],
        "summary": {
            "count": len(values),
            "latest_value": values[-1].value if values else None,
            "min_value": min(v.value for v in values) if values else None,
            "max_value": max(v.value for v in values) if values else None,
            "avg_value": sum(v.value for v in values) / len(values) if values else None
        }
    }


@router.get("/alerts", response_model=List[AlertResponse])
async def get_alerts(
    status: Optional[AlertStatus] = None,
    severity: Optional[AlertSeverity] = None,
    limit: int = Query(50, ge=1, le=1000),
    current_user: UserTable = Depends(require_admin)
):
    """Get alerts with optional filtering."""
    if status == AlertStatus.ACTIVE:
        alerts = alert_manager.get_active_alerts()
    else:
        alerts = alert_manager.get_alert_history(limit=limit)
    
    # Filter by severity if specified
    if severity:
        alerts = [a for a in alerts if a.severity == severity]
    
    # Filter by status if specified and not already filtered to active
    if status and status != AlertStatus.ACTIVE:
        alerts = [a for a in alerts if a.status == status]
    
    return [
        AlertResponse(
            id=alert.id,
            name=alert.name,
            description=alert.description,
            severity=alert.severity.value,
            status=alert.status.value,
            created_at=alert.created_at,
            updated_at=alert.updated_at,
            source=alert.source,
            labels=alert.labels,
            resolved_at=alert.resolved_at,
            acknowledged_at=alert.acknowledged_at,
            acknowledged_by=alert.acknowledged_by
        )
        for alert in alerts
    ]


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    current_user: UserTable = Depends(require_admin)
):
    """Acknowledge an alert."""
    active_alerts = alert_manager.get_active_alerts()
    alert = next((a for a in active_alerts if a.id == alert_id), None)
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found or not active"
        )
    
    alert_manager.acknowledge_alert(alert_id, current_user.email)
    
    return {"message": "Alert acknowledged successfully"}


@router.post("/alerts/{alert_id}/suppress")
async def suppress_alert(
    alert_id: str,
    current_user: UserTable = Depends(require_admin)
):
    """Suppress an alert."""
    active_alerts = alert_manager.get_active_alerts()
    alert = next((a for a in active_alerts if a.id == alert_id), None)
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found or not active"
        )
    
    alert_manager.suppress_alert(alert_id)
    
    return {"message": "Alert suppressed successfully"}


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    time_range: DashboardTimeRange = DashboardTimeRange.LAST_24_HOURS,
    current_user: UserTable = Depends(require_admin)
):
    """Get monitoring dashboard data."""
    dashboard_data = await dashboard.get_dashboard_data(time_range)
    
    return DashboardResponse(
        system_health=dashboard_data.system_health,
        key_metrics=dashboard_data.key_metrics,
        active_alerts=dashboard_data.active_alerts,
        charts=dashboard_data.charts,
        summary=dashboard_data.summary
    )


@router.get("/dashboard/widgets")
async def get_dashboard_widgets(
    current_user: UserTable = Depends(require_admin)
):
    """Get dashboard widget configuration."""
    widgets = dashboard.get_widget_config()
    
    return [
        {
            "id": widget.id,
            "title": widget.title,
            "type": widget.type,
            "data_source": widget.data_source,
            "config": widget.config,
            "position": widget.position
        }
        for widget in widgets
    ]


@router.get("/stats")
async def get_monitoring_stats(
    current_user: UserTable = Depends(require_admin)
):
    """Get monitoring system statistics."""
    active_alerts = alert_manager.get_active_alerts()
    health_results = await health_checker.run_all_checks()
    all_metrics = metrics_collector.get_all_metrics()
    
    # Calculate alert statistics
    alert_stats = {
        "total_active": len(active_alerts),
        "by_severity": {
            "critical": sum(1 for a in active_alerts if a.severity == AlertSeverity.CRITICAL),
            "error": sum(1 for a in active_alerts if a.severity == AlertSeverity.ERROR),
            "warning": sum(1 for a in active_alerts if a.severity == AlertSeverity.WARNING),
            "info": sum(1 for a in active_alerts if a.severity == AlertSeverity.INFO)
        }
    }
    
    # Calculate health statistics
    health_stats = {
        "total_checks": len(health_results),
        "by_status": {
            "healthy": sum(1 for r in health_results.values() if r.status == HealthStatus.HEALTHY),
            "degraded": sum(1 for r in health_results.values() if r.status == HealthStatus.DEGRADED),
            "unhealthy": sum(1 for r in health_results.values() if r.status == HealthStatus.UNHEALTHY),
            "unknown": sum(1 for r in health_results.values() if r.status == HealthStatus.UNKNOWN)
        }
    }
    
    # Calculate metric statistics
    metrics_with_data = sum(1 for m in all_metrics.values() if m["current_value"] is not None)
    
    return {
        "alerts": alert_stats,
        "health": health_stats,
        "metrics": {
            "total_registered": len(all_metrics),
            "with_data": metrics_with_data,
            "collection_active": True
        },
        "system": {
            "monitoring_uptime": "24h",  # Placeholder
            "last_updated": datetime.utcnow().isoformat()
        }
    }


@router.post("/test-alert")
async def trigger_test_alert(
    current_user: UserTable = Depends(require_admin)
):
    """Trigger a test alert for testing purposes."""
    from ..monitoring.alerts import Alert, AlertSeverity, AlertStatus
    
    test_alert = Alert(
        id=f"test_alert_{int(datetime.utcnow().timestamp())}",
        name="test_alert",
        description="This is a test alert triggered manually",
        severity=AlertSeverity.INFO,
        status=AlertStatus.ACTIVE,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        source="manual_test",
        labels={"test": "true", "triggered_by": current_user.email}
    )
    
    alert_manager.active_alerts[test_alert.id] = test_alert
    alert_manager.alert_history.append(test_alert)
    
    return {"message": "Test alert triggered successfully", "alert_id": test_alert.id}


@router.get("/export")
async def export_monitoring_data(
    format: str = Query("json", regex="^(json|csv)$"),
    time_range_hours: int = Query(24, ge=1, le=168),
    current_user: UserTable = Depends(require_admin)
):
    """Export monitoring data."""
    from io import StringIO
    import csv
    import json
    
    # Collect data
    health_results = await health_checker.run_all_checks()
    active_alerts = alert_manager.get_active_alerts()
    all_metrics = metrics_collector.get_all_metrics()
    
    export_data = {
        "export_timestamp": datetime.utcnow().isoformat(),
        "time_range_hours": time_range_hours,
        "health_checks": {
            name: {
                "status": result.status.value,
                "message": result.message,
                "response_time_ms": result.response_time_ms,
                "timestamp": result.timestamp.isoformat()
            }
            for name, result in health_results.items()
        },
        "active_alerts": [
            {
                "id": alert.id,
                "name": alert.name,
                "severity": alert.severity.value,
                "status": alert.status.value,
                "created_at": alert.created_at.isoformat(),
                "description": alert.description
            }
            for alert in active_alerts
        ],
        "metrics": all_metrics
    }
    
    if format == "json":
        return export_data
    else:  # CSV format
        output = StringIO()
        writer = csv.writer(output)
        
        # Write health checks
        writer.writerow(["Type", "Name", "Status", "Message", "Response Time (ms)", "Timestamp"])
        for name, check in export_data["health_checks"].items():
            writer.writerow([
                "Health Check", name, check["status"], check["message"],
                check["response_time_ms"], check["timestamp"]
            ])
        
        # Write alerts
        writer.writerow([])  # Empty row
        writer.writerow(["Type", "ID", "Name", "Severity", "Status", "Created At", "Description"])
        for alert in export_data["active_alerts"]:
            writer.writerow([
                "Alert", alert["id"], alert["name"], alert["severity"],
                alert["status"], alert["created_at"], alert["description"]
            ])
        
        # Write metrics
        writer.writerow([])  # Empty row
        writer.writerow(["Type", "Name", "Current Value", "Unit", "Description", "Last Updated"])
        for name, metric in export_data["metrics"].items():
            writer.writerow([
                "Metric", name, metric["current_value"], metric["unit"],
                metric["description"], metric["last_updated"]
            ])
        
        return {"csv_data": output.getvalue()}