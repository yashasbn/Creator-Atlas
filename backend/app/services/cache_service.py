import time
import json
from typing import Optional, Dict, Any
from app.config import settings
from app.observability.tracer import (
    tracer, 
    cache_operations_total,
    cache_latency,
    elapsed_ms,
    mark_error,
    otel_logger
)

try:
    import redis
    _redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    _redis_available = True
except Exception:
    _redis_client = None
    _redis_available = False

_memory_cache: Dict[str, Dict[str, Any]] = {}

class CacheService:
    @staticmethod
    def get(key: str) -> Optional[Dict[str, Any]]:
        start_time = time.perf_counter()
        formatted_key = f"creator_atlas:{key.lower().strip()}"
        result = None

        with tracer.start_as_current_span("cache.get") as span:
            span.set_attribute("cache.system", "redis" if _redis_available else "memory")

            if _redis_available and _redis_client:
                try:
                    data = _redis_client.get(formatted_key)
                    if data:
                        result = json.loads(data)
                except Exception as e:
                    mark_error(span, e)
                    otel_logger.error(f"Redis cache query error: {e}", extra={"error_details": str(e)})

            if result is None and formatted_key in _memory_cache:
                entry = _memory_cache[formatted_key]
                if entry["expiry"] > time.time():
                    result = entry["data"]

            duration = elapsed_ms(start_time)
            metric_attributes = {"cache.system": "redis" if _redis_available else "memory", "cache.operation": "get"}
            cache_latency.record(duration, metric_attributes)

            if result:
                cache_operations_total.add(1, {**metric_attributes, "cache.result": "hit"})
                span.set_attribute("cache.hit", True)
                otel_logger.info("Cache hit", extra={"execution_time_ms": round(duration, 2), "channel": key})
            else:
                cache_operations_total.add(1, {**metric_attributes, "cache.result": "miss"})
                span.set_attribute("cache.hit", False)
                otel_logger.info("Cache miss", extra={"execution_time_ms": round(duration, 2), "channel": key})

        return result

    @staticmethod
    def set(key: str, value: Dict[str, Any], ttl: int = None) -> None:
        ttl = ttl or settings.CACHE_TTL_SECONDS
        formatted_key = f"creator_atlas:{key.lower().strip()}"
        json_str = json.dumps(value)

        with tracer.start_as_current_span("cache.set") as span:
            span.set_attribute("cache.system", "redis" if _redis_available else "memory")
            span.set_attribute("cache.ttl", ttl)

            if _redis_available and _redis_client:
                try:
                    _redis_client.setex(formatted_key, ttl, json_str)
                    return
                except Exception as e:
                    mark_error(span, e)

            _memory_cache[formatted_key] = {
                "data": value,
                "expiry": time.time() + ttl
            }

    @staticmethod
    def get_stats() -> Dict[str, Any]:
        return {
            "backend": "redis" if _redis_available else "memory_fallback"
        }
