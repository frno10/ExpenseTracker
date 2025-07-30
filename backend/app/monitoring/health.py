"""Health check system for monitoring application status."""
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as redis
import httpx

from ..core.database import get_db
from ..core.config import settings


class HealthStatus(str, Enum):
    """Health check status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    name: str
    status: HealthStatus
    response_time_ms: float
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class HealthChecker:
    """System health monitoring and checking."""
    
    def __init__(self):
        self.checks = {}
        self.last_results = {}
        self.setup_default_checks()
    
    def setup_default_checks(self):
        """Set up default health checks."""
        self.register_check("database", self.check_database)
        self.register_check("redis", self.check_redis)
        self.register_check("disk_space", self.check_disk_space)
        self.register_check("memory", self.check_memory)
        self.register_check("external_apis", self.check_external_apis)
        self.register_check("parser_health", self.check_parser_health)
    
    def register_check(self, name: str, check_func):
        """Register a health check function."""
        self.checks[name] = check_func
    
    async def run_check(self, name: str) -> HealthCheckResult:
        """Run a specific health check."""
        if name not in self.checks:
            return HealthCheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=0,
                message=f"Health check '{name}' not found"
            )
        
        start_time = time.time()
        try:
            result = await self.checks[name]()
            response_time = (time.time() - start_time) * 1000
            
            if isinstance(result, HealthCheckResult):
                result.response_time_ms = response_time
                self.last_results[name] = result
                return result
            else:
                # Handle simple boolean or string results
                status = HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY
                result = HealthCheckResult(
                    name=name,
                    status=status,
                    response_time_ms=response_time,
                    message="OK" if result else "Check failed"
                )
                self.last_results[name] = result
                return result
                
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            result = HealthCheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                message=f"Health check failed: {str(e)}"
            )
            self.last_results[name] = result
            return result
    
    async def run_all_checks(self) -> Dict[str, HealthCheckResult]:
        """Run all registered health checks."""
        results = {}
        
        # Run checks concurrently
        tasks = [self.run_check(name) for name in self.checks.keys()]
        check_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, name in enumerate(self.checks.keys()):
            if isinstance(check_results[i], Exception):
                results[name] = HealthCheckResult(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    response_time_ms=0,
                    message=f"Check failed with exception: {str(check_results[i])}"
                )
            else:
                results[name] = check_results[i]
        
        return results
    
    async def get_overall_health(self) -> Dict[str, Any]:
        """Get overall system health status."""
        results = await self.run_all_checks()
        
        # Determine overall status
        statuses = [result.status for result in results.values()]
        if any(status == HealthStatus.UNHEALTHY for status in statuses):
            overall_status = HealthStatus.UNHEALTHY
        elif any(status == HealthStatus.DEGRADED for status in statuses):
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY
        
        # Calculate average response time
        response_times = [result.response_time_ms for result in results.values()]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        return {
            "status": overall_status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "environment": settings.ENVIRONMENT,
            "uptime_seconds": self.get_uptime(),
            "average_response_time_ms": round(avg_response_time, 2),
            "checks": {name: {
                "status": result.status.value,
                "response_time_ms": result.response_time_ms,
                "message": result.message,
                "details": result.details
            } for name, result in results.items()}
        }
    
    def get_uptime(self) -> float:
        """Get application uptime in seconds."""
        # This would be set when the application starts
        if not hasattr(self, '_start_time'):
            self._start_time = time.time()
        return time.time() - self._start_time
    
    # Individual health check implementations
    async def check_database(self) -> HealthCheckResult:
        """Check database connectivity and performance."""
        try:
            async for db in get_db():
                start_time = time.time()
                
                # Test basic connectivity
                await db.execute(text("SELECT 1"))
                
                # Test table access
                await db.execute(text("SELECT COUNT(*) FROM users LIMIT 1"))
                
                query_time = (time.time() - start_time) * 1000
                
                if query_time > 1000:  # > 1 second
                    return HealthCheckResult(
                        name="database",
                        status=HealthStatus.DEGRADED,
                        response_time_ms=0,
                        message=f"Database responding slowly ({query_time:.2f}ms)",
                        details={"query_time_ms": query_time}
                    )
                
                return HealthCheckResult(
                    name="database",
                    status=HealthStatus.HEALTHY,
                    response_time_ms=0,
                    message="Database connection healthy",
                    details={"query_time_ms": query_time}
                )
                
        except Exception as e:
            return HealthCheckResult(
                name="database",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=0,
                message=f"Database connection failed: {str(e)}"
            )
    
    async def check_redis(self) -> HealthCheckResult:
        """Check Redis connectivity and performance."""
        try:
            redis_client = redis.from_url(settings.REDIS_URL)
            
            start_time = time.time()
            
            # Test basic connectivity
            await redis_client.ping()
            
            # Test read/write operations
            test_key = "health_check_test"
            await redis_client.set(test_key, "test_value", ex=60)
            value = await redis_client.get(test_key)
            await redis_client.delete(test_key)
            
            response_time = (time.time() - start_time) * 1000
            
            if value != b"test_value":
                return HealthCheckResult(
                    name="redis",
                    status=HealthStatus.DEGRADED,
                    response_time_ms=0,
                    message="Redis read/write test failed"
                )
            
            await redis_client.close()
            
            return HealthCheckResult(
                name="redis",
                status=HealthStatus.HEALTHY,
                response_time_ms=0,
                message="Redis connection healthy",
                details={"response_time_ms": response_time}
            )
            
        except Exception as e:
            return HealthCheckResult(
                name="redis",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=0,
                message=f"Redis connection failed: {str(e)}"
            )
    
    async def check_disk_space(self) -> HealthCheckResult:
        """Check available disk space."""
        try:
            import shutil
            
            # Check disk space for the application directory
            total, used, free = shutil.disk_usage("/")
            
            free_percent = (free / total) * 100
            used_percent = (used / total) * 100
            
            if free_percent < 5:  # Less than 5% free
                status = HealthStatus.UNHEALTHY
                message = f"Critical: Only {free_percent:.1f}% disk space remaining"
            elif free_percent < 15:  # Less than 15% free
                status = HealthStatus.DEGRADED
                message = f"Warning: Only {free_percent:.1f}% disk space remaining"
            else:
                status = HealthStatus.HEALTHY
                message = f"Disk space healthy: {free_percent:.1f}% free"
            
            return HealthCheckResult(
                name="disk_space",
                status=status,
                response_time_ms=0,
                message=message,
                details={
                    "total_gb": round(total / (1024**3), 2),
                    "used_gb": round(used / (1024**3), 2),
                    "free_gb": round(free / (1024**3), 2),
                    "used_percent": round(used_percent, 1),
                    "free_percent": round(free_percent, 1)
                }
            )
            
        except Exception as e:
            return HealthCheckResult(
                name="disk_space",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=0,
                message=f"Disk space check failed: {str(e)}"
            )
    
    async def check_memory(self) -> HealthCheckResult:
        """Check memory usage."""
        try:
            import psutil
            
            memory = psutil.virtual_memory()
            used_percent = memory.percent
            available_gb = memory.available / (1024**3)
            
            if used_percent > 90:
                status = HealthStatus.UNHEALTHY
                message = f"Critical: {used_percent:.1f}% memory usage"
            elif used_percent > 80:
                status = HealthStatus.DEGRADED
                message = f"Warning: {used_percent:.1f}% memory usage"
            else:
                status = HealthStatus.HEALTHY
                message = f"Memory usage healthy: {used_percent:.1f}%"
            
            return HealthCheckResult(
                name="memory",
                status=status,
                response_time_ms=0,
                message=message,
                details={
                    "total_gb": round(memory.total / (1024**3), 2),
                    "used_gb": round(memory.used / (1024**3), 2),
                    "available_gb": round(available_gb, 2),
                    "used_percent": round(used_percent, 1)
                }
            )
            
        except Exception as e:
            return HealthCheckResult(
                name="memory",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=0,
                message=f"Memory check failed: {str(e)}"
            )
    
    async def check_external_apis(self) -> HealthCheckResult:
        """Check external API dependencies."""
        try:
            # This would check any external APIs the app depends on
            # For now, we'll just check if we can make HTTP requests
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                start_time = time.time()
                
                # Test HTTP client functionality
                response = await client.get("https://httpbin.org/status/200")
                
                response_time = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    return HealthCheckResult(
                        name="external_apis",
                        status=HealthStatus.HEALTHY,
                        response_time_ms=0,
                        message="External API connectivity healthy",
                        details={"test_response_time_ms": response_time}
                    )
                else:
                    return HealthCheckResult(
                        name="external_apis",
                        status=HealthStatus.DEGRADED,
                        response_time_ms=0,
                        message=f"External API test returned status {response.status_code}"
                    )
                    
        except Exception as e:
            return HealthCheckResult(
                name="external_apis",
                status=HealthStatus.DEGRADED,
                response_time_ms=0,
                message=f"External API check failed: {str(e)}"
            )
    
    async def check_parser_health(self) -> HealthCheckResult:
        """Check parser system health."""
        try:
            from ..parsers.registry import parser_registry
            
            # Check if parsers are registered
            registered_parsers = len(parser_registry.parsers)
            
            if registered_parsers == 0:
                return HealthCheckResult(
                    name="parser_health",
                    status=HealthStatus.UNHEALTHY,
                    response_time_ms=0,
                    message="No parsers registered"
                )
            
            # Test parser initialization
            pdf_parser = parser_registry.find_parser("test.pdf")
            csv_parser = parser_registry.find_parser("test.csv")
            
            if not pdf_parser or not csv_parser:
                return HealthCheckResult(
                    name="parser_health",
                    status=HealthStatus.DEGRADED,
                    response_time_ms=0,
                    message="Some parsers not available",
                    details={"registered_parsers": registered_parsers}
                )
            
            return HealthCheckResult(
                name="parser_health",
                status=HealthStatus.HEALTHY,
                response_time_ms=0,
                message="Parser system healthy",
                details={"registered_parsers": registered_parsers}
            )
            
        except Exception as e:
            return HealthCheckResult(
                name="parser_health",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=0,
                message=f"Parser health check failed: {str(e)}"
            )


# Global health checker instance
health_checker = HealthChecker()