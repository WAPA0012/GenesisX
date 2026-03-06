"""
Metrics collection system for Genesis X.

Provides Prometheus-compatible metrics including counters, gauges, histograms,
system metrics, and application-specific metrics.
"""

import time
import threading
import psutil
import os
from typing import Dict, List, Optional, Any, Callable, Tuple
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json


@dataclass
class MetricValue:
    """Container for a metric value with labels."""
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class Counter:
    """
    Counter metric - monotonically increasing value.

    Used for: requests, errors, completed tasks, etc.
    """

    def __init__(self, name: str, description: str, labels: Optional[List[str]] = None):
        self.name = name
        self.description = description
        self.label_names = labels or []
        self._values = defaultdict(float)
        self._lock = threading.Lock()

    def inc(self, amount: float = 1.0, **labels):
        """Increment counter."""
        label_key = self._make_label_key(labels)
        with self._lock:
            self._values[label_key] += amount

    def get(self, **labels) -> float:
        """Get current counter value."""
        label_key = self._make_label_key(labels)
        with self._lock:
            return self._values[label_key]

    def _make_label_key(self, labels: Dict[str, str]) -> str:
        """Create hashable key from labels."""
        return json.dumps(labels, sort_keys=True)

    def collect(self) -> List[MetricValue]:
        """Collect all counter values."""
        with self._lock:
            return [
                MetricValue(value=v, labels=json.loads(k))
                for k, v in self._values.items()
            ]


class Gauge:
    """
    Gauge metric - value that can go up or down.

    Used for: active connections, queue size, temperature, etc.
    """

    def __init__(self, name: str, description: str, labels: Optional[List[str]] = None):
        self.name = name
        self.description = description
        self.label_names = labels or []
        self._values = defaultdict(float)
        self._lock = threading.Lock()

    def set(self, value: float, **labels):
        """Set gauge to value."""
        label_key = self._make_label_key(labels)
        with self._lock:
            self._values[label_key] = value

    def inc(self, amount: float = 1.0, **labels):
        """Increment gauge."""
        label_key = self._make_label_key(labels)
        with self._lock:
            self._values[label_key] += amount

    def dec(self, amount: float = 1.0, **labels):
        """Decrement gauge."""
        label_key = self._make_label_key(labels)
        with self._lock:
            self._values[label_key] -= amount

    def get(self, **labels) -> float:
        """Get current gauge value."""
        label_key = self._make_label_key(labels)
        with self._lock:
            return self._values[label_key]

    def _make_label_key(self, labels: Dict[str, str]) -> str:
        """Create hashable key from labels."""
        return json.dumps(labels, sort_keys=True)

    def collect(self) -> List[MetricValue]:
        """Collect all gauge values."""
        with self._lock:
            return [
                MetricValue(value=v, labels=json.loads(k))
                for k, v in self._values.items()
            ]


class Histogram:
    """
    Histogram metric - samples observations and counts them in buckets.

    Used for: request durations, response sizes, etc.
    """

    DEFAULT_BUCKETS = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]

    def __init__(self, name: str, description: str,
                 labels: Optional[List[str]] = None,
                 buckets: Optional[List[float]] = None):
        self.name = name
        self.description = description
        self.label_names = labels or []
        self.buckets = buckets or self.DEFAULT_BUCKETS
        self._buckets = defaultdict(lambda: [0] * len(self.buckets))
        self._sums = defaultdict(float)
        self._counts = defaultdict(int)
        self._lock = threading.Lock()

    def observe(self, value: float, **labels):
        """Record an observation."""
        label_key = self._make_label_key(labels)
        with self._lock:
            # Update sum and count
            self._sums[label_key] += value
            self._counts[label_key] += 1

            # Update buckets
            for i, bucket in enumerate(self.buckets):
                if value <= bucket:
                    self._buckets[label_key][i] += 1

    def time(self, **labels):
        """Context manager to time code block."""
        return _HistogramTimer(self, labels)

    def _make_label_key(self, labels: Dict[str, str]) -> str:
        """Create hashable key from labels."""
        return json.dumps(labels, sort_keys=True)

    def collect(self) -> Dict[str, Any]:
        """Collect histogram data."""
        with self._lock:
            data = {}
            for label_key in self._sums.keys():
                labels = json.loads(label_key)
                data[label_key] = {
                    'labels': labels,
                    'sum': self._sums[label_key],
                    'count': self._counts[label_key],
                    'buckets': list(zip(self.buckets, self._buckets[label_key]))
                }
            return data


class _HistogramTimer:
    """Context manager for timing histogram observations."""

    def __init__(self, histogram: Histogram, labels: Dict[str, str]):
        self.histogram = histogram
        self.labels = labels
        self.start_time = None

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.perf_counter() - self.start_time
        self.histogram.observe(duration, **self.labels)


class SystemMetrics:
    """Collector for system-level metrics."""

    def __init__(self):
        self.process = psutil.Process(os.getpid())

    def collect(self) -> Dict[str, float]:
        """Collect current system metrics."""
        try:
            # CPU metrics
            cpu_percent = self.process.cpu_percent(interval=0.1)
            cpu_count = psutil.cpu_count()
            system_cpu = psutil.cpu_percent(interval=0.1)

            # Memory metrics
            memory_info = self.process.memory_info()
            memory_percent = self.process.memory_percent()
            system_memory = psutil.virtual_memory()

            # Disk metrics
            disk_usage = psutil.disk_usage('/')

            # Network metrics (if available)
            try:
                net_io = psutil.net_io_counters()
                net_bytes_sent = net_io.bytes_sent
                net_bytes_recv = net_io.bytes_recv
            except Exception:
                net_bytes_sent = 0
                net_bytes_recv = 0

            return {
                # Process CPU
                'process_cpu_percent': cpu_percent,
                'system_cpu_percent': system_cpu,
                'cpu_count': cpu_count,

                # Process Memory
                'process_memory_rss_bytes': memory_info.rss,
                'process_memory_vms_bytes': memory_info.vms,
                'process_memory_percent': memory_percent,

                # System Memory
                'system_memory_total_bytes': system_memory.total,
                'system_memory_available_bytes': system_memory.available,
                'system_memory_used_bytes': system_memory.used,
                'system_memory_percent': system_memory.percent,

                # Disk
                'disk_total_bytes': disk_usage.total,
                'disk_used_bytes': disk_usage.used,
                'disk_free_bytes': disk_usage.free,
                'disk_percent': disk_usage.percent,

                # Network
                'network_bytes_sent_total': net_bytes_sent,
                'network_bytes_recv_total': net_bytes_recv,

                # Process info
                'process_threads': self.process.num_threads(),
                'process_open_fds': self.process.num_fds() if hasattr(self.process, 'num_fds') else 0,
            }
        except Exception as e:
            return {'error': str(e)}


class MetricsCollector:
    """
    Central metrics collection system for Genesis X.

    Provides Prometheus-compatible metrics and custom application metrics.
    """

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
        """Initialize metrics system."""
        if hasattr(self, '_initialized'):
            return

        self._initialized = True
        self._metrics = {}
        self._system_metrics = SystemMetrics()
        self._start_time = time.time()

        # Initialize standard application metrics
        self._init_standard_metrics()

    def _init_standard_metrics(self):
        """Initialize standard application metrics."""
        # HTTP/API metrics
        self.http_requests_total = self.counter(
            'http_requests_total',
            'Total HTTP requests',
            ['method', 'path', 'status']
        )

        self.http_request_duration_seconds = self.histogram(
            'http_request_duration_seconds',
            'HTTP request duration in seconds',
            ['method', 'path'],
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0]
        )

        # Genesis X specific metrics
        self.tick_count_total = self.counter(
            'genesis_tick_count_total',
            'Total number of ticks executed',
            ['organ']
        )

        self.tick_duration_seconds = self.histogram(
            'genesis_tick_duration_seconds',
            'Tick execution duration',
            ['organ'],
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]
        )

        self.active_organs = self.gauge(
            'genesis_active_organs',
            'Number of active organs'
        )

        self.tool_executions_total = self.counter(
            'genesis_tool_executions_total',
            'Total tool executions',
            ['tool', 'status']
        )

        self.tool_execution_duration_seconds = self.histogram(
            'genesis_tool_execution_duration_seconds',
            'Tool execution duration',
            ['tool'],
            buckets=[0.01, 0.1, 0.5, 1.0, 5.0, 10.0, 30.0]
        )

        self.llm_requests_total = self.counter(
            'genesis_llm_requests_total',
            'Total LLM API requests',
            ['model', 'status']
        )

        self.llm_tokens_total = self.counter(
            'genesis_llm_tokens_total',
            'Total LLM tokens used',
            ['model', 'type']  # type: input/output
        )

        self.llm_request_duration_seconds = self.histogram(
            'genesis_llm_request_duration_seconds',
            'LLM request duration',
            ['model'],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
        )

        self.errors_total = self.counter(
            'genesis_errors_total',
            'Total errors by type',
            ['error_type', 'component']
        )

        self.queue_size = self.gauge(
            'genesis_queue_size',
            'Size of processing queues',
            ['queue_name']
        )

        self.memory_mb = self.gauge(
            'genesis_memory_usage_mb',
            'Memory usage in MB',
            ['component']
        )

    def counter(self, name: str, description: str, labels: Optional[List[str]] = None) -> Counter:
        """Create or get a counter metric."""
        if name not in self._metrics:
            self._metrics[name] = Counter(name, description, labels)
        return self._metrics[name]

    def gauge(self, name: str, description: str, labels: Optional[List[str]] = None) -> Gauge:
        """Create or get a gauge metric."""
        if name not in self._metrics:
            self._metrics[name] = Gauge(name, description, labels)
        return self._metrics[name]

    def histogram(self, name: str, description: str,
                  labels: Optional[List[str]] = None,
                  buckets: Optional[List[float]] = None) -> Histogram:
        """Create or get a histogram metric."""
        if name not in self._metrics:
            self._metrics[name] = Histogram(name, description, labels, buckets)
        return self._metrics[name]

    def collect_all(self) -> Dict[str, Any]:
        """Collect all metrics."""
        metrics_data = {
            'timestamp': datetime.now(timezone.utc).isoformat() + 'Z',
            'uptime_seconds': time.time() - self._start_time,
            'metrics': {},
            'system': self._system_metrics.collect()
        }

        for name, metric in self._metrics.items():
            if isinstance(metric, (Counter, Gauge)):
                values = metric.collect()
                metrics_data['metrics'][name] = {
                    'type': metric.__class__.__name__.lower(),
                    'description': metric.description,
                    'values': [
                        {'value': v.value, 'labels': v.labels}
                        for v in values
                    ]
                }
            elif isinstance(metric, Histogram):
                metrics_data['metrics'][name] = {
                    'type': 'histogram',
                    'description': metric.description,
                    'data': metric.collect()
                }

        return metrics_data

    def export_prometheus(self) -> str:
        """Export metrics in Prometheus text format."""
        lines = []

        for name, metric in self._metrics.items():
            # Add HELP and TYPE
            lines.append(f"# HELP {name} {metric.description}")

            if isinstance(metric, Counter):
                lines.append(f"# TYPE {name} counter")
                for value in metric.collect():
                    labels_str = self._format_labels(value.labels)
                    lines.append(f"{name}{labels_str} {value.value}")

            elif isinstance(metric, Gauge):
                lines.append(f"# TYPE {name} gauge")
                for value in metric.collect():
                    labels_str = self._format_labels(value.labels)
                    lines.append(f"{name}{labels_str} {value.value}")

            elif isinstance(metric, Histogram):
                lines.append(f"# TYPE {name} histogram")
                for label_key, data in metric.collect().items():
                    labels = data['labels']
                    labels_str = self._format_labels(labels)

                    # Buckets
                    for bucket_val, count in data['buckets']:
                        bucket_labels = {**labels, 'le': str(bucket_val)}
                        bucket_str = self._format_labels(bucket_labels)
                        lines.append(f"{name}_bucket{bucket_str} {count}")

                    # +Inf bucket
                    inf_labels = {**labels, 'le': '+Inf'}
                    inf_str = self._format_labels(inf_labels)
                    lines.append(f"{name}_bucket{inf_str} {data['count']}")

                    # Sum and count
                    lines.append(f"{name}_sum{labels_str} {data['sum']}")
                    lines.append(f"{name}_count{labels_str} {data['count']}")

        # Add system metrics
        system_metrics = self._system_metrics.collect()
        for key, value in system_metrics.items():
            if key != 'error':
                lines.append(f"# TYPE system_{key} gauge")
                lines.append(f"system_{key} {value}")

        return '\n'.join(lines) + '\n'

    def _format_labels(self, labels: Dict[str, str]) -> str:
        """Format labels for Prometheus."""
        if not labels:
            return ''
        label_pairs = [f'{k}="{v}"' for k, v in sorted(labels.items())]
        return '{' + ','.join(label_pairs) + '}'


# Global metrics collector instance
_metrics_collector = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance."""
    return _metrics_collector


def metrics_endpoint_handler() -> Tuple[str, str, int]:
    """
    Handler for /metrics endpoint.

    Returns:
        Tuple of (content, content_type, status_code)
    """
    try:
        collector = get_metrics_collector()
        content = collector.export_prometheus()
        return content, 'text/plain; version=0.0.4', 200
    except Exception as e:
        return f"Error collecting metrics: {str(e)}", 'text/plain', 500
