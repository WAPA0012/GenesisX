"""
Health check system for Genesis X.

Provides /health and /ready endpoints for monitoring system health,
dependency status, and readiness for traffic.
"""

import time
import threading
from typing import Dict, List, Optional, Callable, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import logging


class HealthStatus(Enum):
    """Health check status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class CheckResult:
    """Result of a health check."""
    name: str
    status: HealthStatus
    message: str
    duration_ms: float
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'status': self.status.value,
            'message': self.message,
            'duration_ms': self.duration_ms,
            'timestamp': self.timestamp.isoformat() + 'Z',
            'metadata': self.metadata
        }


class HealthCheck:
    """Base class for health checks."""

    def __init__(self, name: str, timeout: float = 5.0):
        """
        Initialize health check.

        Args:
            name: Check name
            timeout: Check timeout in seconds
        """
        self.name = name
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)

    def check(self) -> CheckResult:
        """
        Perform health check.

        Returns:
            CheckResult
        """
        start_time = time.perf_counter()

        try:
            result = self._perform_check()
            duration_ms = (time.perf_counter() - start_time) * 1000

            return CheckResult(
                name=self.name,
                status=result.get('status', HealthStatus.HEALTHY),
                message=result.get('message', 'OK'),
                duration_ms=duration_ms,
                timestamp=datetime.now(timezone.utc),
                metadata=result.get('metadata', {})
            )
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self.logger.error(f"Health check '{self.name}' failed: {e}")

            return CheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Check failed: {str(e)}",
                duration_ms=duration_ms,
                timestamp=datetime.now(timezone.utc),
                metadata={'error': str(e)}
            )

    def _perform_check(self) -> Dict[str, Any]:
        """
        Implement actual check logic.

        Returns:
            Dict with 'status', 'message', and optional 'metadata'
        """
        raise NotImplementedError


class DatabaseHealthCheck(HealthCheck):
    """Health check for database connectivity."""

    def __init__(self, name: str = "database", db_connector: Optional[Callable] = None):
        """
        Initialize database health check.

        Args:
            name: Check name
            db_connector: Function that returns database connection
        """
        super().__init__(name)
        self.db_connector = db_connector

    def _perform_check(self) -> Dict[str, Any]:
        """Check database connectivity."""
        if not self.db_connector:
            return {
                'status': HealthStatus.DEGRADED,
                'message': 'Database connector not configured'
            }

        try:
            # Attempt to get connection and execute simple query
            conn = self.db_connector()
            if hasattr(conn, 'ping'):
                conn.ping()

            return {
                'status': HealthStatus.HEALTHY,
                'message': 'Database connection OK'
            }
        except Exception as e:
            return {
                'status': HealthStatus.UNHEALTHY,
                'message': f'Database connection failed: {str(e)}'
            }


class LLMAPIHealthCheck(HealthCheck):
    """Health check for LLM API availability."""

    def __init__(self, name: str = "llm_api", api_checker: Optional[Callable] = None):
        """
        Initialize LLM API health check.

        Args:
            name: Check name
            api_checker: Function that checks API availability
        """
        super().__init__(name)
        self.api_checker = api_checker

    def _perform_check(self) -> Dict[str, Any]:
        """Check LLM API availability."""
        if not self.api_checker:
            return {
                'status': HealthStatus.DEGRADED,
                'message': 'LLM API checker not configured'
            }

        try:
            # Check API availability
            result = self.api_checker()

            if result.get('available', False):
                return {
                    'status': HealthStatus.HEALTHY,
                    'message': 'LLM API available',
                    'metadata': result
                }
            else:
                return {
                    'status': HealthStatus.DEGRADED,
                    'message': 'LLM API degraded',
                    'metadata': result
                }
        except Exception as e:
            return {
                'status': HealthStatus.UNHEALTHY,
                'message': f'LLM API check failed: {str(e)}'
            }


class DiskSpaceHealthCheck(HealthCheck):
    """Health check for disk space."""

    def __init__(self, name: str = "disk_space", path: str = "/", warn_percent: float = 80.0):
        """
        Initialize disk space health check.

        Args:
            name: Check name
            path: Path to check
            warn_percent: Warning threshold percentage
        """
        super().__init__(name)
        self.path = path
        self.warn_percent = warn_percent

    def _perform_check(self) -> Dict[str, Any]:
        """Check disk space."""
        try:
            import psutil
            disk = psutil.disk_usage(self.path)

            percent_used = disk.percent

            if percent_used >= 95:
                status = HealthStatus.UNHEALTHY
                message = f"Disk space critical: {percent_used:.1f}% used"
            elif percent_used >= self.warn_percent:
                status = HealthStatus.DEGRADED
                message = f"Disk space low: {percent_used:.1f}% used"
            else:
                status = HealthStatus.HEALTHY
                message = f"Disk space OK: {percent_used:.1f}% used"

            return {
                'status': status,
                'message': message,
                'metadata': {
                    'percent_used': percent_used,
                    'total_gb': disk.total / (1024**3),
                    'free_gb': disk.free / (1024**3)
                }
            }
        except Exception as e:
            return {
                'status': HealthStatus.UNHEALTHY,
                'message': f'Disk check failed: {str(e)}'
            }


class MemoryHealthCheck(HealthCheck):
    """Health check for memory usage."""

    def __init__(self, name: str = "memory", warn_percent: float = 85.0):
        """
        Initialize memory health check.

        Args:
            name: Check name
            warn_percent: Warning threshold percentage
        """
        super().__init__(name)
        self.warn_percent = warn_percent

    def _perform_check(self) -> Dict[str, Any]:
        """Check memory usage."""
        try:
            import psutil
            memory = psutil.virtual_memory()

            percent_used = memory.percent

            if percent_used >= 95:
                status = HealthStatus.UNHEALTHY
                message = f"Memory critical: {percent_used:.1f}% used"
            elif percent_used >= self.warn_percent:
                status = HealthStatus.DEGRADED
                message = f"Memory high: {percent_used:.1f}% used"
            else:
                status = HealthStatus.HEALTHY
                message = f"Memory OK: {percent_used:.1f}% used"

            return {
                'status': status,
                'message': message,
                'metadata': {
                    'percent_used': percent_used,
                    'total_gb': memory.total / (1024**3),
                    'available_gb': memory.available / (1024**3)
                }
            }
        except Exception as e:
            return {
                'status': HealthStatus.UNHEALTHY,
                'message': f'Memory check failed: {str(e)}'
            }


class HealthCheckSystem:
    """Central health check system."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize health check system."""
        if hasattr(self, '_initialized'):
            return

        self._initialized = True
        self.logger = logging.getLogger(__name__)
        self.start_time = time.time()

        # Separate checks for liveness and readiness
        self.liveness_checks: List[HealthCheck] = []
        self.readiness_checks: List[HealthCheck] = []

        # Cache results
        self._cache_duration = 10.0  # seconds
        self._liveness_cache = None
        self._liveness_cache_time = 0
        self._readiness_cache = None
        self._readiness_cache_time = 0

        # Register default checks
        self._register_default_checks()

    def _register_default_checks(self):
        """Register default health checks."""
        # Liveness checks (basic system health)
        self.add_liveness_check(DiskSpaceHealthCheck())
        self.add_liveness_check(MemoryHealthCheck())

        # Readiness checks (can handle traffic)
        self.add_readiness_check(DiskSpaceHealthCheck(warn_percent=90))
        self.add_readiness_check(MemoryHealthCheck(warn_percent=90))

    def add_liveness_check(self, check: HealthCheck):
        """Add a liveness check."""
        self.liveness_checks.append(check)

    def add_readiness_check(self, check: HealthCheck):
        """Add a readiness check."""
        self.readiness_checks.append(check)

    def check_liveness(self, use_cache: bool = True) -> Dict[str, Any]:
        """
        Check if application is alive.

        Args:
            use_cache: Use cached result if available

        Returns:
            Health check results
        """
        if use_cache and self._liveness_cache:
            cache_age = time.time() - self._liveness_cache_time
            if cache_age < self._cache_duration:
                return self._liveness_cache

        results = []
        overall_status = HealthStatus.HEALTHY

        for check in self.liveness_checks:
            result = check.check()
            results.append(result)

            if result.status == HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.UNHEALTHY
            elif result.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.DEGRADED

        response = {
            'status': overall_status.value,
            'timestamp': datetime.now(timezone.utc).isoformat() + 'Z',
            'uptime_seconds': time.time() - self.start_time,
            'checks': [r.to_dict() for r in results]
        }

        self._liveness_cache = response
        self._liveness_cache_time = time.time()

        return response

    def check_readiness(self, use_cache: bool = True) -> Dict[str, Any]:
        """
        Check if application is ready to handle traffic.

        Args:
            use_cache: Use cached result if available

        Returns:
            Health check results
        """
        if use_cache and self._readiness_cache:
            cache_age = time.time() - self._readiness_cache_time
            if cache_age < self._cache_duration:
                return self._readiness_cache

        results = []
        overall_status = HealthStatus.HEALTHY

        for check in self.readiness_checks:
            result = check.check()
            results.append(result)

            if result.status == HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.UNHEALTHY
            elif result.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.DEGRADED

        response = {
            'status': overall_status.value,
            'timestamp': datetime.now(timezone.utc).isoformat() + 'Z',
            'uptime_seconds': time.time() - self.start_time,
            'checks': [r.to_dict() for r in results]
        }

        self._readiness_cache = response
        self._readiness_cache_time = time.time()

        return response


# Global health check system
_health_check_system = HealthCheckSystem()


def get_health_check_system() -> HealthCheckSystem:
    """Get the global health check system instance."""
    return _health_check_system


def health_endpoint_handler() -> Tuple[Dict[str, Any], int]:
    """
    Handler for /health endpoint (liveness probe).

    Returns:
        Tuple of (response_dict, status_code)
    """
    try:
        system = get_health_check_system()
        result = system.check_liveness()

        status_code = 200 if result['status'] == 'healthy' else 503
        return result, status_code
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat() + 'Z'
        }, 500


def ready_endpoint_handler() -> Tuple[Dict[str, Any], int]:
    """
    Handler for /ready endpoint (readiness probe).

    Returns:
        Tuple of (response_dict, status_code)
    """
    try:
        system = get_health_check_system()
        result = system.check_readiness()

        status_code = 200 if result['status'] == 'healthy' else 503
        return result, status_code
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat() + 'Z'
        }, 500
