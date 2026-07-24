import time
from typing import Dict, Any

_request_count = 0
_total_duration = 0.0

def record_request_metric(duration_seconds: float):
    global _request_count, _total_duration
    _request_count += 1
    _total_duration += duration_seconds

def get_metrics_data() -> Dict[str, Any]:
    avg_latency = (_total_duration / _request_count) if _request_count > 0 else 0.0
    return {
        "requests_total": _request_count,
        "avg_request_duration_seconds": round(avg_latency, 4),
    }
