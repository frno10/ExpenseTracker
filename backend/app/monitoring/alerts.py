"""Alerting system for monitoring critical events and thresholds."""
import asyncio
import smtplib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.database import get_db
from .metrics import metrics_collector, MetricValue


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    """Alert status."""
    ACTIVE = "active"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"
    SUPPRESSED = "suppressed"


@dataclass
class AlertRule:
    """Definition of an alert rule."""
    name: str
    description: str
    metric_name: str
    condition: str  # e.g., ">", "<", "==", "!="
    threshold: float
    severity: AlertSeverity
    duration: timedelta = field(default_factory=lambda: timedelta(minutes=5))
    cooldown: timedelta = field(default_factory=lambda: timedelta(minutes=30))
    enabled: bool = True
    labels: Dict[str, str] = field(default_factory=dict)
    
    def evaluate(self, metric_value: Optional[float]) -> bool:
        """Evaluate if the alert condition is met."""
        if metric_value is None:
            return False
        
        if self.condition == ">":
            return metric_value > self.threshold
        elif self.condition == "<":
            return metric_value < self.threshold
        elif self.condition == ">=":
            return metric_value >= self.threshold
        elif self.condition == "<=":
            return metric_value <= self.threshold
        elif self.condition == "==":
            return metric_value == self.threshold
        elif self.condition == "!=":
            return metric_value != self.threshold
        
        return False


@dataclass
class Alert:
    """An active or resolved alert."""
    id: str
    rule_name: str
    severity: AlertSeverity
    status: AlertStatus
    message: str
    metric_name: str
    metric_value: float
    threshold: float
    started_at: datetime
    resolved_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)


class AlertManager:
    """Manage alerts and notifications."""
    
    def __init__(self):
        self.rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.notification_channels = []
        self.evaluation_task = None
        self.setup_default_rules()
    
    def setup_default_rules(self):
        """Set up default alert rules."""
        # System alerts
        self.add_rule(AlertRule(
            name="high_memory_usage",
            description="Memory usage is critically high",
            metric_name="memory_usage",
            condition=">",
            threshold=0.9,  # 90%
            severity=AlertSeverity.CRITICAL,
            duration=timedelta(minutes=2)
        ))
        
        self.add_rule(AlertRule(
            name="high_cpu_usage",
            description="CPU usage is high",
            metric_name="cpu_usage",
            condition=">",
            threshold=80.0,  # 80%
            severity=AlertSeverity.HIGH,
            duration=timedelta(minutes=5)
        ))
        
        self.add_rule(AlertRule(
            name="low_disk_space",
            description="Disk space is running low",
            metric_name="disk_free_percent",
            condition="<",
            threshold=10.0,  # 10%
            severity=AlertSeverity.HIGH,
            duration=timedelta(minutes=1)
        ))
        
        # Business alerts
        self.add_rule(AlertRule(
            name="parser_failure_rate_high",
            description="Parser failure rate is too high",
            metric_name="parser_success_rate",
            condition="<",
            threshold=80.0,  # 80%
            severity=AlertSeverity.MEDIUM,
            duration=timedelta(minutes=10)
        ))
        
        self.add_rule(AlertRule(
            name="failed_login_spike",
            description="Unusual number of failed login attempts",
            metric_name="failed_login_attempts_total",
            condition=">",
            threshold=50,
            severity=AlertSeverity.HIGH,
            duration=timedelta(minutes=5)
        ))
        
        self.add_rule(AlertRule(
            name="no_active_users",
            description="No active users detected",
            metric_name="active_users",
            condition="==",
            threshold=0,
            severity=AlertSeverity.MEDIUM,
            duration=timedelta(hours=2)
        ))
        
        # Performance alerts
        self.add_rule(AlertRule(
            name="high_response_time",
            description="API response time is too high",
            metric_name="response_time_p95",
            condition=">",
            threshold=2000,  # 2 seconds
            severity=AlertSeverity.MEDIUM,
            duration=timedelta(minutes=5)
        ))
        
        self.add_rule(AlertRule(
            name="high_error_rate",
            description="Error rate is too high",
            metric_name="error_rate",
            condition=">",
            threshold=5.0,  # 5%
            severity=AlertSeverity.HIGH,
            duration=timedelta(minutes=3)
        ))
    
    def add_rule(self, rule: AlertRule):
        """Add an alert rule."""
        self.rules[rule.name] = rule
    
    def remove_rule(self, rule_name: str):
        """Remove an alert rule."""
        if rule_name in self.rules:
            del self.rules[rule_name]
    
    def enable_rule(self, rule_name: str):
        """Enable an alert rule."""
        if rule_name in self.rules:
            self.rules[rule_name].enabled = True
    
    def disable_rule(self, rule_name: str):
        """Disable an alert rule."""
        if rule_name in self.rules:
            self.rules[rule_name].enabled = False
    
    async def start_evaluation(self):
        """Start the alert evaluation loop."""
        if self.evaluation_task is None:
            self.evaluation_task = asyncio.create_task(self._evaluation_loop())
    
    async def stop_evaluation(self):
        """Stop the alert evaluation loop."""
        if self.evaluation_task:
            self.evaluation_task.cancel()
            self.evaluation_task = None
    
    async def _evaluation_loop(self):
        """Main alert evaluation loop."""
        while True:
            try:
                await self.evaluate_all_rules()
                await asyncio.sleep(30)  # Evaluate every 30 seconds
            except Exception as e:
                print(f"Error in alert evaluation loop: {e}")
                await asyncio.sleep(60)
    
    async def evaluate_all_rules(self):
        """Evaluate all alert rules."""
        for rule_name, rule in self.rules.items():
            if not rule.enabled:
                continue
            
            try:
                await self.evaluate_rule(rule)
            except Exception as e:
                print(f"Error evaluating rule {rule_name}: {e}")
    
    async def evaluate_rule(self, rule: AlertRule):
        """Evaluate a single alert rule."""
        # Get current metric value
        if rule.metric_name not in metrics_collector.metrics:
            return
        
        metric = metrics_collector.metrics[rule.metric_name]
        current_value = metric.get_current_value()
        
        # Check if condition is met
        condition_met = rule.evaluate(current_value)
        
        alert_id = f"{rule.name}_{rule.metric_name}"
        
        if condition_met:
            # Check if alert already exists
            if alert_id in self.active_alerts:
                # Alert already active, check if it should be escalated
                alert = self.active_alerts[alert_id]
                duration_active = datetime.utcnow() - alert.started_at
                
                if duration_active >= rule.duration and alert.status == AlertStatus.ACTIVE:
                    # Alert has been active long enough, ensure notifications are sent
                    await self.send_notifications(alert)
            else:
                # Create new alert
                alert = Alert(
                    id=alert_id,
                    rule_name=rule.name,
                    severity=rule.severity,
                    status=AlertStatus.ACTIVE,
                    message=f"{rule.description}. Current value: {current_value}, Threshold: {rule.threshold}",
                    metric_name=rule.metric_name,
                    metric_value=current_value or 0,
                    threshold=rule.threshold,
                    started_at=datetime.utcnow(),
                    labels=rule.labels.copy()
                )
                
                self.active_alerts[alert_id] = alert
                
                # Wait for duration before sending notifications
                await asyncio.sleep(rule.duration.total_seconds())
                
                # Re-check condition after duration
                current_value = metrics_collector.metrics[rule.metric_name].get_current_value()
                if rule.evaluate(current_value):
                    await self.send_notifications(alert)
        else:
            # Condition not met, resolve alert if it exists
            if alert_id in self.active_alerts:
                alert = self.active_alerts[alert_id]
                alert.status = AlertStatus.RESOLVED
                alert.resolved_at = datetime.utcnow()
                
                # Move to history
                self.alert_history.append(alert)
                del self.active_alerts[alert_id]
                
                # Send resolution notification
                await self.send_resolution_notification(alert)
    
    async def send_notifications(self, alert: Alert):
        """Send notifications for an alert."""
        for channel in self.notification_channels:
            try:
                await channel(alert)
            except Exception as e:
                print(f"Error sending notification: {e}")
    
    async def send_resolution_notification(self, alert: Alert):
        """Send notification when alert is resolved."""
        resolution_message = f"RESOLVED: {alert.message}"
        resolved_alert = Alert(
            id=alert.id,
            rule_name=alert.rule_name,
            severity=alert.severity,
            status=AlertStatus.RESOLVED,
            message=resolution_message,
            metric_name=alert.metric_name,
            metric_value=alert.metric_value,
            threshold=alert.threshold,
            started_at=alert.started_at,
            resolved_at=alert.resolved_at,
            labels=alert.labels
        )
        
        for channel in self.notification_channels:
            try:
                await channel(resolved_alert)
            except Exception as e:
                print(f"Error sending resolution notification: {e}")
    
    def add_notification_channel(self, channel: Callable):
        """Add a notification channel."""
        self.notification_channels.append(channel)
    
    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str):
        """Acknowledge an alert."""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.status = AlertStatus.ACKNOWLEDGED
            alert.acknowledged_at = datetime.utcnow()
            alert.acknowledged_by = acknowledged_by
    
    async def suppress_alert(self, alert_id: str, duration: timedelta):
        """Suppress an alert for a specified duration."""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.status = AlertStatus.SUPPRESSED
            
            # Schedule unsuppression
            async def unsuppress():
                await asyncio.sleep(duration.total_seconds())
                if alert_id in self.active_alerts:
                    self.active_alerts[alert_id].status = AlertStatus.ACTIVE
            
            asyncio.create_task(unsuppress())
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts."""
        return list(self.active_alerts.values())
    
    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """Get alert history."""
        return self.alert_history[-limit:]
    
    async def get_alert_summary(self) -> Dict[str, Any]:
        """Get alert summary for dashboard."""
        active_alerts = self.get_active_alerts()
        
        # Count by severity
        severity_counts = {
            AlertSeverity.CRITICAL: 0,
            AlertSeverity.HIGH: 0,
            AlertSeverity.MEDIUM: 0,
            AlertSeverity.LOW: 0
        }
        
        for alert in active_alerts:
            severity_counts[alert.severity] += 1
        
        # Recent resolved alerts
        recent_resolved = [
            alert for alert in self.alert_history
            if alert.resolved_at and alert.resolved_at > datetime.utcnow() - timedelta(hours=24)
        ]
        
        return {
            "active_alerts_count": len(active_alerts),
            "severity_breakdown": {
                "critical": severity_counts[AlertSeverity.CRITICAL],
                "high": severity_counts[AlertSeverity.HIGH],
                "medium": severity_counts[AlertSeverity.MEDIUM],
                "low": severity_counts[AlertSeverity.LOW]
            },
            "recent_resolved_count": len(recent_resolved),
            "active_alerts": [
                {
                    "id": alert.id,
                    "rule_name": alert.rule_name,
                    "severity": alert.severity.value,
                    "status": alert.status.value,
                    "message": alert.message,
                    "started_at": alert.started_at.isoformat(),
                    "duration_minutes": (datetime.utcnow() - alert.started_at).total_seconds() / 60
                }
                for alert in active_alerts
            ]
        }


# Notification channel implementations
async def email_notification_channel(alert: Alert):
    """Send email notifications."""
    if not hasattr(settings, 'SMTP_HOST') or not settings.SMTP_HOST:
        return
    
    try:
        msg = MIMEMultipart()
        msg['From'] = settings.SMTP_FROM
        msg['To'] = settings.ALERT_EMAIL_TO
        msg['Subject'] = f"[{alert.severity.upper()}] {alert.rule_name}"
        
        body = f"""
        Alert: {alert.rule_name}
        Severity: {alert.severity.upper()}
        Status: {alert.status.upper()}
        
        Message: {alert.message}
        
        Metric: {alert.metric_name}
        Current Value: {alert.metric_value}
        Threshold: {alert.threshold}
        
        Started At: {alert.started_at}
        
        Labels: {json.dumps(alert.labels, indent=2)}
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
        if settings.SMTP_TLS:
            server.starttls()
        if settings.SMTP_USERNAME:
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        
        server.send_message(msg)
        server.quit()
        
    except Exception as e:
        print(f"Failed to send email notification: {e}")


async def webhook_notification_channel(alert: Alert):
    """Send webhook notifications."""
    if not hasattr(settings, 'ALERT_WEBHOOK_URL') or not settings.ALERT_WEBHOOK_URL:
        return
    
    try:
        payload = {
            "alert_id": alert.id,
            "rule_name": alert.rule_name,
            "severity": alert.severity.value,
            "status": alert.status.value,
            "message": alert.message,
            "metric_name": alert.metric_name,
            "metric_value": alert.metric_value,
            "threshold": alert.threshold,
            "started_at": alert.started_at.isoformat(),
            "labels": alert.labels,
            "annotations": alert.annotations
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.ALERT_WEBHOOK_URL,
                json=payload,
                timeout=10.0
            )
            response.raise_for_status()
            
    except Exception as e:
        print(f"Failed to send webhook notification: {e}")


async def slack_notification_channel(alert: Alert):
    """Send Slack notifications."""
    if not hasattr(settings, 'SLACK_WEBHOOK_URL') or not settings.SLACK_WEBHOOK_URL:
        return
    
    try:
        # Color based on severity
        color_map = {
            AlertSeverity.CRITICAL: "#FF0000",
            AlertSeverity.HIGH: "#FF8C00",
            AlertSeverity.MEDIUM: "#FFD700",
            AlertSeverity.LOW: "#32CD32"
        }
        
        payload = {
            "attachments": [
                {
                    "color": color_map.get(alert.severity, "#808080"),
                    "title": f"{alert.severity.upper()}: {alert.rule_name}",
                    "text": alert.message,
                    "fields": [
                        {
                            "title": "Metric",
                            "value": alert.metric_name,
                            "short": True
                        },
                        {
                            "title": "Current Value",
                            "value": str(alert.metric_value),
                            "short": True
                        },
                        {
                            "title": "Threshold",
                            "value": str(alert.threshold),
                            "short": True
                        },
                        {
                            "title": "Started At",
                            "value": alert.started_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
                            "short": True
                        }
                    ],
                    "footer": "Expense Tracker Monitoring",
                    "ts": int(alert.started_at.timestamp())
                }
            ]
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.SLACK_WEBHOOK_URL,
                json=payload,
                timeout=10.0
            )
            response.raise_for_status()
            
    except Exception as e:
        print(f"Failed to send Slack notification: {e}")


# Global alert manager instance
alert_manager = AlertManager()

# Set up default notification channels
alert_manager.add_notification_channel(email_notification_channel)
alert_manager.add_notification_channel(webhook_notification_channel)
alert_manager.add_notification_channel(slack_notification_channel)