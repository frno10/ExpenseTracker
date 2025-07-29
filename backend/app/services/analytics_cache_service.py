"""
Analytics caching service for improved performance.
"""
import json
import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, Optional, List
from uuid import UUID
from hashlib import md5

from app.core.config import settings

logger = logging.getLogger(__name__)


class AnalyticsCacheService:
    """Service for caching analytics results to improve performance."""
    
    def __init__(self):
        self.cache = {}  # In-memory cache for development
        self.cache_ttl = {
            "dashboard": 300,  # 5 minutes
            "time_series": 600,  # 10 minutes
            "category_trends": 900,  # 15 minutes
            "monthly_comparison": 1800,  # 30 minutes
            "anomalies": 3600,  # 1 hour
        }
    
    def _generate_cache_key(
        self,
        cache_type: str,
        user_id: UUID,
        **kwargs
    ) -> str:
        """Generate a unique cache key."""
        
        # Create a consistent key from parameters
        key_data = {
            "type": cache_type,
            "user_id": str(user_id),
            **kwargs
        }
        
        # Sort keys for consistency
        sorted_data = json.dumps(key_data, sort_keys=True, default=str)
        
        # Generate hash
        key_hash = md5(sorted_data.encode()).hexdigest()
        
        return f"analytics:{cache_type}:{key_hash}"
    
    def _is_cache_valid(self, cache_entry: Dict[str, Any]) -> bool:
        """Check if cache entry is still valid."""
        
        if not cache_entry:
            return False
        
        cached_at = datetime.fromisoformat(cache_entry["cached_at"])
        ttl = cache_entry.get("ttl", 300)  # Default 5 minutes
        
        return datetime.utcnow() < cached_at + timedelta(seconds=ttl)
    
    def get_cached_result(
        self,
        cache_type: str,
        user_id: UUID,
        **kwargs
    ) -> Optional[Any]:
        """Get cached analytics result."""
        
        cache_key = self._generate_cache_key(cache_type, user_id, **kwargs)
        cache_entry = self.cache.get(cache_key)
        
        if cache_entry and self._is_cache_valid(cache_entry):
            logger.info(f"Cache hit for {cache_type} - user {user_id}")
            return cache_entry["data"]
        
        logger.info(f"Cache miss for {cache_type} - user {user_id}")
        return None
    
    def cache_result(
        self,
        cache_type: str,
        user_id: UUID,
        data: Any,
        **kwargs
    ) -> None:
        """Cache analytics result."""
        
        cache_key = self._generate_cache_key(cache_type, user_id, **kwargs)
        ttl = self.cache_ttl.get(cache_type, 300)
        
        cache_entry = {
            "data": data,
            "cached_at": datetime.utcnow().isoformat(),
            "ttl": ttl
        }
        
        self.cache[cache_key] = cache_entry
        logger.info(f"Cached {cache_type} result for user {user_id} (TTL: {ttl}s)")
    
    def invalidate_user_cache(self, user_id: UUID) -> None:
        """Invalidate all cache entries for a user."""
        
        keys_to_remove = []
        user_id_str = str(user_id)
        
        for key, entry in self.cache.items():
            if user_id_str in key:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.cache[key]
        
        logger.info(f"Invalidated {len(keys_to_remove)} cache entries for user {user_id}")
    
    def invalidate_cache_type(self, cache_type: str) -> None:
        """Invalidate all cache entries of a specific type."""
        
        keys_to_remove = []
        
        for key in self.cache.keys():
            if f"analytics:{cache_type}:" in key:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.cache[key]
        
        logger.info(f"Invalidated {len(keys_to_remove)} {cache_type} cache entries")
    
    def clear_expired_cache(self) -> None:
        """Clear expired cache entries."""
        
        keys_to_remove = []
        
        for key, entry in self.cache.items():
            if not self._is_cache_valid(entry):
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.cache[key]
        
        logger.info(f"Cleared {len(keys_to_remove)} expired cache entries")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        
        total_entries = len(self.cache)
        valid_entries = sum(1 for entry in self.cache.values() if self._is_cache_valid(entry))
        expired_entries = total_entries - valid_entries
        
        # Count by type
        type_counts = {}
        for key in self.cache.keys():
            if key.startswith("analytics:"):
                cache_type = key.split(":")[1]
                type_counts[cache_type] = type_counts.get(cache_type, 0) + 1
        
        return {
            "total_entries": total_entries,
            "valid_entries": valid_entries,
            "expired_entries": expired_entries,
            "type_breakdown": type_counts,
            "cache_ttl_settings": self.cache_ttl
        }


# Redis-based cache service for production
class RedisAnalyticsCacheService(AnalyticsCacheService):
    """Redis-based analytics cache service for production use."""
    
    def __init__(self, redis_client=None):
        super().__init__()
        self.redis = redis_client
        self.key_prefix = "expense_tracker:analytics:"
    
    def _generate_cache_key(
        self,
        cache_type: str,
        user_id: UUID,
        **kwargs
    ) -> str:
        """Generate a Redis cache key."""
        
        base_key = super()._generate_cache_key(cache_type, user_id, **kwargs)
        return f"{self.key_prefix}{base_key}"
    
    def get_cached_result(
        self,
        cache_type: str,
        user_id: UUID,
        **kwargs
    ) -> Optional[Any]:
        """Get cached result from Redis."""
        
        if not self.redis:
            return super().get_cached_result(cache_type, user_id, **kwargs)
        
        try:
            cache_key = self._generate_cache_key(cache_type, user_id, **kwargs)
            cached_data = self.redis.get(cache_key)
            
            if cached_data:
                logger.info(f"Redis cache hit for {cache_type} - user {user_id}")
                return json.loads(cached_data)
            
            logger.info(f"Redis cache miss for {cache_type} - user {user_id}")
            return None
            
        except Exception as e:
            logger.error(f"Redis cache get error: {e}")
            return None
    
    def cache_result(
        self,
        cache_type: str,
        user_id: UUID,
        data: Any,
        **kwargs
    ) -> None:
        """Cache result in Redis."""
        
        if not self.redis:
            return super().cache_result(cache_type, user_id, data, **kwargs)
        
        try:
            cache_key = self._generate_cache_key(cache_type, user_id, **kwargs)
            ttl = self.cache_ttl.get(cache_type, 300)
            
            # Serialize data
            serialized_data = json.dumps(data, default=str)
            
            # Store in Redis with TTL
            self.redis.setex(cache_key, ttl, serialized_data)
            
            logger.info(f"Cached {cache_type} result in Redis for user {user_id} (TTL: {ttl}s)")
            
        except Exception as e:
            logger.error(f"Redis cache set error: {e}")
    
    def invalidate_user_cache(self, user_id: UUID) -> None:
        """Invalidate all Redis cache entries for a user."""
        
        if not self.redis:
            return super().invalidate_user_cache(user_id)
        
        try:
            pattern = f"{self.key_prefix}*{user_id}*"
            keys = self.redis.keys(pattern)
            
            if keys:
                self.redis.delete(*keys)
                logger.info(f"Invalidated {len(keys)} Redis cache entries for user {user_id}")
            
        except Exception as e:
            logger.error(f"Redis cache invalidation error: {e}")
    
    def clear_expired_cache(self) -> None:
        """Redis automatically handles TTL, so this is a no-op."""
        pass
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get Redis cache statistics."""
        
        if not self.redis:
            return super().get_cache_stats()
        
        try:
            # Get all analytics keys
            pattern = f"{self.key_prefix}*"
            keys = self.redis.keys(pattern)
            
            # Count by type
            type_counts = {}
            for key in keys:
                key_str = key.decode() if isinstance(key, bytes) else key
                if ":analytics:" in key_str:
                    parts = key_str.split(":")
                    if len(parts) >= 3:
                        cache_type = parts[2]
                        type_counts[cache_type] = type_counts.get(cache_type, 0) + 1
            
            return {
                "total_entries": len(keys),
                "type_breakdown": type_counts,
                "cache_ttl_settings": self.cache_ttl,
                "redis_info": self.redis.info() if hasattr(self.redis, 'info') else {}
            }
            
        except Exception as e:
            logger.error(f"Redis cache stats error: {e}")
            return {"error": str(e)}


# Create service instance
try:
    # Try to import Redis for production use
    import redis
    
    # Check if Redis is configured
    redis_url = getattr(settings, 'REDIS_URL', None)
    if redis_url:
        redis_client = redis.from_url(redis_url)
        analytics_cache_service = RedisAnalyticsCacheService(redis_client)
        logger.info("Using Redis analytics cache service")
    else:
        analytics_cache_service = AnalyticsCacheService()
        logger.info("Using in-memory analytics cache service")
        
except ImportError:
    analytics_cache_service = AnalyticsCacheService()
    logger.info("Redis not available, using in-memory analytics cache service")