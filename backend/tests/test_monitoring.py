"""Tests for monitoring and alerting system."""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from app.monitoring.health import HealthChecker, HealthStatus, HealthCheckResult
from app.monitoring.metrics import MetricsCollector, MetricType, Metric
from app.monitoring.alerts import AlertManager, AlertRule, AlertSeverity, Alert, AlertStatus


class TestHealthChecker:
    """Test health checking functionality."""
    
    def test_health_checker_initialization(self):
        """Test health checker initializes with default checks."""
        checker = HealthChecker()
        
        assert "database" in checker.checks
        assert "redis" in checker.checks
        assert "disk_space" in checker.checks
        assert "memory" in checker.checks
        assert "external_apis" in checker.checks
        assert "parser_health" in checker.checks
    
    @pytest.mark.asyncio
    async def test_run_check_success(self):
        """Test successful health check execution."""
        checker = HealthChecker()
        
        # Mock a simple check
        async def mock_check():
            return HealthCheckResult(
                name="test_check",
                status=HealthStatus.HEALTHY,
                response_time_ms=0,
                message="Test check passed"
            )
        
        checker.register_check("test_check", mock_check)
        result = await checker.run_check("test_check")
        
        assert result.name == "test_check"
        assert result.status == HealthStatus.HEALTHY
        assert result.message == "Test check passed"
    
    @pytest.mark.asyncio
    async def test_run_check_failure(self):
        """Test health check failure handling."""
        checker = HealthChecker()
        
        # Mock a failing check
        async def mock_failing_check():
            raise Exception("Check failed")
        
        checker.register_check("failing_check", mock_failing_check)
        result = await checker.run_check("failing_check")
        
        assert result.name == "failing_check"
        assert result.status == HealthStatus.UNHEALTHY
        assert "Check failed" in result.message
    
    @pytest.mark.asyncio
    async def test_run_all_checks(self):
        """Test running all health checks."""
        checker = HealthChecker()
        
        # Add mock checks
        async def healthy_check():
            return HealthCheckResult("healthy", HealthStatus.HEALTHY, 0, "OK")
        
        async def unhealthy_check():
            return HealthCheckResult("unhealthy", HealthStatus.UNHEALTHY, 0, "Failed")
        
        checker.checks = {
            "healthy": healthy_check,
            "unhealthy": unhealthy_check
        }
        
        results = await checker.run_all_checks()
        
        assert len(results) == 2
        assert results["healthy"].status == HealthStatus.HEALTHY
        assert results["unhealthy"].status == HealthStatus.UNHEALTHY
    
    @pytest.mark.asyncio
    async def test_overall_health_calculation(self):
        """Test overall health status calculation."""
        checker = HealthChecker()
        
        # Mock checks with different statuses
        async def healthy_check():
            return HealthCheckResult("healthy", HealthStatus.HEALTHY, 10, "OK")
        
        async def degraded_check():
            return HealthCheckResult("degraded", HealthStatus.DEGRADED, 20, "Slow")
        
        checker.checks = {
            "healthy": healthy_check,
            "degraded": degraded_check
        }
        
        overall_health = await checker.get_overall_health()
        
        assert overall_health["status"] == "degraded"  # Should be degraded due to one degraded check
        assert "checks" in overall_health
        assert len(overall_health["checks"]) == 2


class TestMetricsCollector:
    """Test metrics collection functionality."""
    
    def test_metrics_collector_initialization(self):
        """Test metrics collector initializes with default metrics."""
        collector = MetricsCollector()
        
        assert "http_requests_total" in collector.metrics
        assert "active_users" in collector.metrics
        assert "expenses_created_total" in collector.metrics
        assert "parser_success_rate" in collector.metrics
    
    def test_register_metric(self):
        """Test metric registration."""
        collector = MetricsCollector()
        
        collector.register_metric(
            "test_metric",
            MetricType.COUNTER,
            "Test metric description",
            "units"
        )
        
        assert "test_metric" in collector.metrics
        metric = collector.metrics["test_metric"]
        assert metric.name == "test_metric"
        assert metric.type == MetricType.COUNTER
        assert metric.description == "Test metric description"
        assert metric.unit == "units"
    
    def test_increment_counter(self):
        """Test counter metric increment."""
        collector = MetricsCollector()
        
        collector.register_metric("test_counter", MetricType.COUNTER, "Test counter")
        
        # Increment counter
        collector.increment_counter("test_counter", 5)
        assert collector.metrics["test_counter"].get_current_value() == 5
        
        # Increment again
        collector.increment_counter("test_counter", 3)
        assert collector.metrics["test_counter"].get_current_value() == 8
    
    def test_set_gauge(self):
        """Test gauge metric setting."""
        collector = MetricsCollector()
        
        collector.register_metric("test_gauge", MetricType.GAUGE, "Test gauge")
        
        # Set gauge value
        collector.set_gauge("test_gauge", 42.5)
        assert collector.metrics["test_gauge"].get_current_value() == 42.5
        
        # Set new value
        collector.set_gauge("test_gauge", 100.0)
        assert collector.metrics["test_gauge"].get_current_value() == 100.0
    
    def test_record_histogram(self):
        """Test histogram metric recording."""
        collector = MetricsCollector()
        
        collector.register_metric("test_histogram", MetricType.HISTOGRAM, "Test histogram")
        
        # Record values
        collector.record_histogram("test_histogram", 10.5)
        collector.record_histogram("test_histogram", 20.3)
        
        metric = collector.metrics["test_histogram"]
        assert len(metric.values) == 2
        assert metric.get_current_value() == 20.3  # Latest value
    
    @pytest.mark.asyncio
    async def test_metrics_summary(self):
        """Test metrics summary generation."""
        collector = MetricsCollector()
        
        # Add some test metrics
        collector.register_metric("test_counter", MetricType.COUNTER, "Test counter")
        collector.increment_counter("test_counter", 10)
        
        summary = await collector.get_metrics_summary()
        
        assert "timestamp" in summary
        assert "metrics" in summary
        assert "test_counter" in summary["metrics"]
        
        counter_data = summary["metrics"]["test_counter"]
        assert counter_data["type"] == "counter"
        assert counter_data["current_value"] == 10
        assert counter_data["description"] == "Test counter"


class TestAlertManager:
    """Test alerting functionality."""
    
    def test_alert_manager_initialization(self):
        """Test alert manager initializes with default rules."""
        manager = AlertManager()
        
        assert "high_memory_usage" in manager.rules
        assert "parser_failure_rate_high" in manager.rules
        assert "failed_login_spike" in manager.rules
        assert "high_response_time" in manager.rules
    
    def test_add_alert_rule(self):
        """Test adding alert rules."""
        manager = AlertManager()
        
        rule = AlertRule(
            name="test_rule",
            description="Test alert rule",
            metric_name="test_metric",
            condition=">",
            threshold=100.0,
            severity=AlertSeverity.HIGH
        )
        
        manager.add_rule(rule)
        
        assert "test_rule" in manager.rules
        assert manager.rules["test_rule"].threshold == 100.0
        assert manager.rules["test_rule"].severity == AlertSeverity.HIGH
    
    def test_alert_rule_evaluation(self):
        """Test alert rule condition evaluation."""
        rule = AlertRule(
            name="test_rule",
            description="Test rule",
            metric_name="test_metric",
            condition=">",
            threshold=50.0,
            severity=AlertSeverity.MEDIUM
        )
        
        # Test different conditions
        assert rule.evaluate(60.0) is True   # 60 > 50
        assert rule.evaluate(40.0) is False  # 40 > 50
        assert rule.evaluate(50.0) is False  # 50 > 50
        
        # Test different operators
        rule.condition = ">="
        assert rule.evaluate(50.0) is True   # 50 >= 50
        
        rule.condition = "<"
        assert rule.evaluate(40.0) is True   # 40 < 50
        
        rule.condition = "=="
        assert rule.evaluate(50.0) is True   # 50 == 50
    
    @pytest.mark.asyncio
    async def test_alert_creation(self):
        """Test alert creation when conditions are met."""
        manager = AlertManager()
        
        # Mock metrics collector
        with patch('app.monitoring.alerts.metrics_collector') as mock_collector:
            mock_metric = Mock()
            mock_metric.get_current_value.return_value = 95.0
            mock_collector.metrics = {"test_metric": mock_metric}
            
            # Add a rule that should trigger
            rule = AlertRule(
                name="test_alert",
                description="Test alert",
                metric_name="test_metric",
                condition=">",
                threshold=90.0,
                severity=AlertSeverity.HIGH,
                duration=timedelta(seconds=1)  # Short duration for testing
            )
            
            manager.add_rule(rule)
            
            # Evaluate the rule
            await manager.evaluate_rule(rule)
            
            # Check if alert was created
            alert_id = "test_alert_test_metric"
            assert alert_id in manager.active_alerts
            
            alert = manager.active_alerts[alert_id]
            assert alert.rule_name == "test_alert"
            assert alert.severity == AlertSeverity.HIGH
            assert alert.status == AlertStatus.ACTIVE
    
    @pytest.mark.asyncio
    async def test_alert_resolution(self):
        """Test alert resolution when conditions are no longer met."""
        manager = AlertManager()
        
        # Create an active alert
        alert = Alert(
            id="test_alert_id",
            rule_name="test_rule",
            severity=AlertSeverity.MEDIUM,
            status=AlertStatus.ACTIVE,
            message="Test alert",
            metric_name="test_metric",
            metric_value=95.0,
            threshold=90.0,
            started_at=datetime.utcnow()
        )
        
        manager.active_alerts["test_alert_id"] = alert
        
        # Mock metrics collector with value below threshold
        with patch('app.monitoring.alerts.metrics_collector') as mock_collector:
            mock_metric = Mock()
            mock_metric.get_current_value.return_value = 85.0  # Below threshold
            mock_collector.metrics = {"test_metric": mock_metric}
            
            rule = AlertRule(
                name="test_rule",
                description="Test rule",
                metric_name="test_metric",
                condition=">",
                threshold=90.0,
                severity=AlertSeverity.MEDIUM
            )
            
            # Evaluate the rule
            await manager.evaluate_rule(rule)
            
            # Check if alert was resolved
            assert "test_alert_id" not in manager.active_alerts
            assert len(manager.alert_history) == 1
            assert manager.alert_history[0].status == AlertStatus.RESOLVED
    
    def test_alert_acknowledgment(self):
        """Test alert acknowledgment."""
        manager = AlertManager()
        
        # Create an active alert
        alert = Alert(
            id="test_alert_id",
            rule_name="test_rule",
            severity=AlertSeverity.HIGH,
            status=AlertStatus.ACTIVE,
            message="Test alert",
            metric_name="test_metric",
            metric_value=95.0,
            threshold=90.0,
            started_at=datetime.utcnow()
        )
        
        manager.active_alerts["test_alert_id"] = alert
        
        # Acknowledge the alert
        asyncio.run(manager.acknowledge_alert("test_alert_id", "user123"))
        
        # Check acknowledgment
        acknowledged_alert = manager.active_alerts["test_alert_id"]
        assert acknowledged_alert.status == AlertStatus.ACKNOWLEDGED
        assert acknowledged_alert.acknowledged_by == "user123"
        assert acknowledged_alert.acknowledged_at is not None
    
    @pytest.mark.asyncio
    async def test_alert_summary(self):
        """Test alert summary generation."""
        manager = AlertManager()
        
        # Create test alerts with different severities
        alerts = [
            Alert("alert1", "rule1", AlertSeverity.CRITICAL, AlertStatus.ACTIVE, "Critical alert", "metric1", 100, 90, datetime.utcnow()),
            Alert("alert2", "rule2", AlertSeverity.HIGH, AlertStatus.ACTIVE, "High alert", "metric2", 80, 70, datetime.utcnow()),
            Alert("alert3", "rule3", AlertSeverity.MEDIUM, AlertStatus.ACTIVE, "Medium alert", "metric3", 60, 50, datetime.utcnow()),
        ]
        
        for alert in alerts:
            manager.active_alerts[alert.id] = alert
        
        summary = await manager.get_alert_summary()
        
        assert summary["active_alerts_count"] == 3
        assert summary["severity_breakdown"]["critical"] == 1
        assert summary["severity_breakdown"]["high"] == 1
        assert summary["severity_breakdown"]["medium"] == 1
        assert summary["severity_breakdown"]["low"] == 0
        assert len(summary["active_alerts"]) == 3


class TestMonitoringIntegration:
    """Test monitoring system integration."""
    
    @pytest.mark.asyncio
    async def test_monitoring_dashboard_overview(self):
        """Test monitoring dashboard system overview."""
        from app.monitoring.dashboard import MonitoringDashboard
        
        # Mock all components
        with patch('app.monitoring.dashboard.health_checker') as mock_health, \
             patch('app.monitoring.dashboard.metrics_collector') as mock_metrics, \
             patch('app.monitoring.dashboard.alert_manager') as mock_alerts:
            
            # Mock health status
            mock_health.get_overall_health.return_value = {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Mock metrics
            mock_metrics.get_dashboard_metrics.return_value = {
                "system": {"active_users": 10},
                "business": {"expenses_created_today": 5}
            }
            
            # Mock alerts
            mock_alerts.get_alert_summary.return_value = {
                "active_alerts_count": 2,
                "severity_breakdown": {"critical": 1, "high": 1, "medium": 0, "low": 0}
            }
            
            overview = await MonitoringDashboard.get_system_overview()
            
            assert "timestamp" in overview
            assert "health" in overview
            assert "metrics" in overview
            assert "alerts" in overview
            assert overview["status"] == "operational"
    
    @pytest.mark.asyncio
    async def test_end_to_end_monitoring_flow(self):
        """Test complete monitoring flow from metrics to alerts."""
        # This would test the complete flow:
        # 1. Metrics collection
        # 2. Alert rule evaluation
        # 3. Alert creation
        # 4. Notification sending
        # 5. Dashboard display
        
        collector = MetricsCollector()
        manager = AlertManager()
        
        # Set up metric and alert rule
        collector.register_metric("test_metric", MetricType.GAUGE, "Test metric")
        
        rule = AlertRule(
            name="test_alert",
            description="Test alert",
            metric_name="test_metric",
            condition=">",
            threshold=80.0,
            severity=AlertSeverity.HIGH,
            duration=timedelta(seconds=1)
        )
        
        manager.add_rule(rule)
        
        # Set metric value that should trigger alert
        collector.set_gauge("test_metric", 90.0)
        
        # Mock the metrics collector in alert manager
        with patch.object(manager, 'metrics_collector', collector):
            # Evaluate rules
            await manager.evaluate_rule(rule)
            
            # Check if alert was created
            alert_id = "test_alert_test_metric"
            assert alert_id in manager.active_alerts
            
            alert = manager.active_alerts[alert_id]
            assert alert.metric_value == 90.0
            assert alert.threshold == 80.0
            assert alert.severity == AlertSeverity.HIGH