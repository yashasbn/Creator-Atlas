import json
import time
from typing import Optional, Dict, Any
from app.config import settings

try:
    import redis
    _redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    _redis_available = True
except Exception:
    _redis_client = None
    _redis_available = False

# Memory fallback cache if Redis is not running
_memory_cache: Dict[str, Dict[str, Any]] = {}
_cache_hits = 0
_cache_misses = 0

class CacheService:
    @staticmethod
    def get(key: str) -> Optional[Dict[str, Any]]:
        global _cache_hits, _cache_misses
        start_time = time.time()
        
        formatted_key = f"creator_atlas:{key.lower().strip()}"
        result = None

        if _redis_available and _redis_client:
            try:
                data = _redis_client.get(formatted_key)
                if data:
                    result = json.loads(data)
            except Exception as e:
                print(f"Redis get error: {e}")

        if result is None and formatted_key in _memory_cache:
            entry = _memory_cache[formatted_key]
            if entry["expiry"] > time.time():
                result = entry["data"]
            else:
                del _memory_cache[formatted_key]

        if result:
            _cache_hits += 1
        else:
            _cache_misses += 1

        return result

    @staticmethod
    def set(key: str, value: Dict[str, Any], ttl: int = None) -> None:
        ttl = ttl or settings.CACHE_TTL_SECONDS
        formatted_key = f"creator_atlas:{key.lower().strip()}"
        json_str = json.dumps(value)

        if _redis_available and _redis_client:
            try:
                _redis_client.setex(formatted_key, ttl, json_str)
                return
            except Exception as e:
                print(f"Redis set error: {e}")

        _memory_cache[formatted_key] = {
            "data": value,
            "expiry": time.time() + ttl
        }

    @staticmethod
    def get_stats() -> Dict[str, Any]:
        total = _cache_hits + _cache_misses
        ratio = (_cache_hits / total) * 100 if total > 0 else 0.0
        return {
            "hits": _cache_hits,
            "misses": _cache_misses,
            "hit_ratio_percentage": round(ratio, 2),
            "backend": "redis" if _redis_available else "memory_fallback"
        }
