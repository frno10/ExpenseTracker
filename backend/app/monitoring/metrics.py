"""Business metrics collection and monitoring system."""
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, func, select
import redis.asyncio as redis

from ..core.database import get_db
from ..core.config import settings


class MetricType(str, Enum):
    """Types of metrics."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class MetricValue:
    """A metric value with timestamp."""
    value: Union[int, float]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class Metric:
    """A metric definition."""
    name: str
    type: MetricType
    description: str
    unit: str = ""
    values: deque = field(default_factory=lambda: deque(maxlen=1000))
    
    def add_value(self, value: Union[int, float], labels: Dict[str, str] = None):
        """Add a value to the metric."""
        self.values.append(MetricValue(
            value=value,
            labels=labels or {}
        ))
    
    def get_current_value(self) -> Optional[Union[int, float]]:
        """Get the most recent value."""
        return self.values[-1].value if self.values else None
    
    def get_values_since(self, since: datetime) -> List[MetricValue]:
        """Get values since a specific time."""
        return [v for v in self.values if v.timestamp >= since]


class MetricsCollector:
    """Collect and manage application metrics."""
    
    def __init__(self):
        self.metrics: Dict[str, Metric] = {}
        self.redis_client = None
        self.setup_default_metrics()
        self._collection_tasks = []
    
    async def initialize(self):
        """Initialize the metrics collector."""
        try:
            self.redis_client = redis.from_url(settings.REDIS_URL)
            await self.redis_client.ping()
        except Exception:
            self.redis_client = None
        
        # Start background collection tasks
        self._collection_tasks = [
            asyncio.create_task(self.collect_system_metrics()),
            asyncio.create_task(self.collect_business_metrics()),
            asyncio.create_task(self.collect_parser_metrics()),
        ]
    
    def setup_default_metrics(self):
        """Set up default metrics to collect."""
        # System metrics
        self.register_metric("http_requests_total", MetricType.COUNTER, "Total HTTP requests")
        self.register_metric("http_request_duration", MetricType.HISTOGRAM, "HTTP request duration", "seconds")
        self.register_metric("active_users", MetricType.GAUGE, "Number of active users")
        self.register_metric("database_connections", MetricType.GAUGE, "Active database connections")
        
        # Business metrics
        self.register_metric("expenses_created_total", MetricType.COUNTER, "Total expenses created")
        self.register_metric("budgets_created_total", MetricType.COUNTER, "Total budgets created")
        self.register_metric("statements_imported_total", MetricType.COUNTER, "Total statements imported")
        self.register_metric("parser_success_rate", MetricType.GAUGE, "Parser success rate", "percentage")
        self.register_metric("user_registrations_total", MetricType.COUNTER, "Total user registrations")
        self.register_metric("login_attempts_total", MetricType.COUNTER, "Total login attempts")
        self.register_metric("failed_login_attempts_total", MetricType.COUNTER, "Failed login attempts")
        
        # Performance metrics
        self.register_metric("response_time_p95", MetricType.GAUGE, "95th percentile response time", "ms")
        self.register_metric("error_rate", MetricType.GAUGE, "Error rate", "percentage")
        self.register_metric("memory_usage", MetricType.GAUGE, "Memory usage", "bytes")
        self.register_metric("cpu_usage", MetricType.GAUGE, "CPU usage", "percentage")
    
    def register_metric(self, name: str, metric_type: MetricType, description: str, unit: str = ""):
        """Register a new metric."""
        self.metrics[name] = Metric(
            name=name,
            type=metric_type,
            description=description,
            unit=unit
        )
    
    def increment_counter(self, name: str, value: int = 1, labels: Dict[str, str] = None):
        """Increment a counter metric."""
        if name in self.metrics and self.metrics[name].type == MetricType.COUNTER:
            current = self.metrics[name].get_current_value() or 0
            self.metrics[name].add_value(current + value, labels)
    
    def set_gauge(self, name: str, value: Union[int, float], labels: Dict[str, str] = None):
        """Set a gauge metric value."""
        if name in self.metrics and self.metrics[name].type == MetricType.GAUGE:
            self.metrics[name].add_value(value, labels)
    
    def record_histogram(self, name: str, value: Union[int, float], labels: Dict[str, str] = None):
        """Record a histogram value."""
        if name in self.metrics and self.metrics[name].type == MetricType.HISTOGRAM:
            self.metrics[name].add_value(value, labels)
    
    def time_function(self, metric_name: str):
        """Decorator to time function execution."""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    duration = (time.time() - start_time) * 1000  # Convert to ms
                    self.record_histogram(metric_name, duration)
                    return result
                except Exception as e:
                    duration = (time.time() - start_time) * 1000
                    self.record_histogram(metric_name, duration, {"status": "error"})
                    raise
            return wrapper
        return decorator
    
    async def collect_system_metrics(self):
        """Collect system-level metrics periodically."""
        while True:
            try:
                # Memory usage
                try:
                    import psutil
                    memory = psutil.virtual_memory()
                    self.set_gauge("memory_usage", memory.used)
                    
                    # CPU usage
                    cpu_percent = psutil.cpu_percent(interval=1)
                    self.set_gauge("cpu_usage", cpu_percent)
                except ImportError:
                    pass
                
                # Database connections (if available)
                try:
                    async for db in get_db():
                        # This would need to be implemented based on your connection pool
                        # For now, we'll just set a placeholder
                        self.set_gauge("database_connections", 1)
                        break
                except Exception:
                    pass
                
                await asyncio.sleep(30)  # Collect every 30 seconds
                
            except Exception as e:
                print(f"Error collecting system metrics: {e}")
                await asyncio.sleep(60)
    
    async def collect_business_metrics(self):
        """Collect business-specific metrics periodically."""
        while True:
            try:
                async for db in get_db():
                    # Active users (users who logged in within last 24 hours)
                    active_users_query = text("""
                        SELECT COUNT(DISTINCT user_id) 
                        FROM audit_logs 
                        WHERE event_type = 'login' 
                        AND timestamp > NOW() - INTERVAL '24 hours'
                    """)
                    result = await db.execute(active_users_query)
                    active_users = result.scalar() or 0
                    self.set_gauge("active_users", active_users)
                    
                    # Total expenses created today
                    expenses_today_query = text("""
                        SELECT COUNT(*) 
                        FROM expenses 
                        WHERE DATE(created_at) = CURRENT_DATE
                    """)
                    result = await db.execute(expenses_today_query)
                    expenses_today = result.scalar() or 0
                    self.increment_counter("expenses_created_total", expenses_today)
                    
                    # Total budgets created today
                    budgets_today_query = text("""
                        SELECT COUNT(*) 
                        FROM budgets 
                        WHERE DATE(created_at) = CURRENT_DATE
                    """)
                    result = await db.execute(budgets_today_query)
                    budgets_today = result.scalar() or 0
                    self.increment_counter("budgets_created_total", budgets_today)
                    
                    # Failed login attempts in last hour
                    failed_logins_query = text("""
                        SELECT COUNT(*) 
                        FROM audit_logs 
                        WHERE event_type = 'login_failed' 
                        AND timestamp > NOW() - INTERVAL '1 hour'
                    """)
                    result = await db.execute(failed_logins_query)
                    failed_logins = result.scalar() or 0
                    self.set_gauge("failed_login_attempts_total", failed_logins)
                    
                    break
                
                await asyncio.sleep(300)  # Collect every 5 minutes
                
            except Exception as e:
                print(f"Error collecting business metrics: {e}")
                await asyncio.sleep(600)
    
    async def collect_parser_metrics(self):
        """Collect parser-specific metrics."""
        while True:
            try:
                async for db in get_db():
                    # Parser success rate
                    parser_stats_query = text("""
                        SELECT 
                            COUNT(*) as total_imports,
                            SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_imports
                        FROM audit_logs 
                        WHERE event_type = 'import' 
                        AND timestamp > NOW() - INTERVAL '24 hours'
                    """)
                    result = await db.execute(parser_stats_query)
                    row = result.fetchone()
                    
                    if row and row.total_imports > 0:
                        success_rate = (row.successful_imports / row.total_imports) * 100
                        self.set_gauge("parser_success_rate", success_rate)
                        self.increment_counter("statements_imported_total", row.total_imports)
                    
                    break
                
                await asyncio.sleep(600)  # Collect every 10 minutes
                
            except Exception as e:
                print(f"Error collecting parser metrics: {e}")
                await asyncio.sleep(600)
    
    async def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of all metrics."""
        summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": {}
        }
        
        for name, metric in self.metrics.items():
            current_value = metric.get_current_value()
            
            # Get values from last hour for trend analysis
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            recent_values = metric.get_values_since(one_hour_ago)
            
            summary["metrics"][name] = {
                "type": metric.type.value,
                "description": metric.description,
                "unit": metric.unit,
                "current_value": current_value,
                "values_last_hour": len(recent_values),
                "trend": self._calculate_trend(recent_values) if len(recent_values) > 1 else None
            }
        
        return summary
    
    def _calculate_trend(self, values: List[MetricValue]) -> str:
        """Calculate trend direction from values."""
        if len(values) < 2:
            return "stable"
        
        first_half = values[:len(values)//2]
        second_half = values[len(values)//2:]
        
        first_avg = sum(v.value for v in first_half) / len(first_half)
        second_avg = sum(v.value for v in second_half) / len(second_half)
        
        if second_avg > first_avg * 1.1:
            return "increasing"
        elif second_avg < first_avg * 0.9:
            return "decreasing"
        else:
            return "stable"
    
    async def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Get metrics formatted for dashboard display."""
        return {
            "system": {
                "active_users": self.metrics["active_users"].get_current_value() or 0,
                "memory_usage_mb": (self.metrics["memory_usage"].get_current_value() or 0) / (1024 * 1024),
                "cpu_usage_percent": self.metrics["cpu_usage"].get_current_value() or 0,
                "database_connections": self.metrics["database_connections"].get_current_value() or 0,
            },
            "business": {
                "expenses_created_today": self.metrics["expenses_created_total"].get_current_value() or 0,
                "budgets_created_today": self.metrics["budgets_created_total"].get_current_value() or 0,
                "parser_success_rate": self.metrics["parser_success_rate"].get_current_value() or 0,
                "failed_logins_last_hour": self.metrics["failed_login_attempts_total"].get_current_value() or 0,
            },
            "performance": {
                "response_time_p95": self.metrics["response_time_p95"].get_current_value() or 0,
                "error_rate": self.metrics["error_rate"].get_current_value() or 0,
            }
        }
    
    async def export_metrics_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []
        
        for name, metric in self.metrics.items():
            # Add metric help
            lines.append(f"# HELP {name} {metric.description}")
            lines.append(f"# TYPE {name} {metric.type.value}")
            
            current_value = metric.get_current_value()
            if current_value is not None:
                lines.append(f"{name} {current_value}")
        
        return "\n".join(lines)
    
    async def cleanup(self):
        """Clean up resources."""
        # Cancel collection tasks
        for task in self._collection_tasks:
            task.cancel()
        
        # Close Redis connection
        if self.redis_client:
            await self.redis_client.close()


# Global metrics collector instance
metrics_collector = MetricsCollector()