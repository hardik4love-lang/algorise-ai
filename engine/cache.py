import json
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Optional

import redis.asyncio as redis
from redis.asyncio import Redis

from engine.config import get_settings
from engine.logging import get_logger
from engine.metrics import REDIS_OPERATIONS, REDIS_OPERATION_DURATION, record_error

logger = get_logger(__name__)
settings = get_settings()


class RedisManager:
    """Redis connection manager with caching utilities."""

    def __init__(self):
        self._client: Optional[Redis] = None
        self._pool: Optional[redis.ConnectionPool] = None

    async def initialize(self) -> None:
        """Initialize Redis connection pool."""
        self._pool = redis.ConnectionPool.from_url(
            settings.redis_url,
            max_connections=settings.redis_max_connections,
            decode_responses=True,
        )
        self._client = redis.Redis(connection_pool=self._pool)

        # Test connection
        try:
            await self._client.ping()
            logger.info("Redis connection established", url=settings.redis_url)
        except Exception as e:
            logger.warning("Redis connection failed", error=str(e))
            raise

    async def close(self) -> None:
        """Close Redis connections."""
        if self._client:
            await self._client.close()
        if self._pool:
            await self._pool.disconnect()
        self._client = None
        self._pool = None

    @property
    def client(self) -> Redis:
        if self._client is None:
            raise RuntimeError("Redis not initialized. Call initialize() first.")
        return self._client

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[redis.Redis, None]:
        """Execute a transaction."""
        async with self.client.pipeline(transaction=True) as pipe:
            try:
                yield pipe
                await pipe.execute()
            except Exception:
                await pipe.reset()
                raise

    # Cache operations with metrics
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        import time
        start = time.perf_counter()
        try:
            value = await self.client.get(key)
            if value:
                return json.loads(value)
            REDIS_OPERATIONS.labels(operation="get", status="miss").inc()
            return None
        except Exception as e:
            REDIS_OPERATIONS.labels(operation="get", status="error").inc()
            record_error("redis_get_error", "cache")
            raise
        finally:
            REDIS_OPERATION_DURATION.labels(operation="get").observe(time.perf_counter() - start)

    async def set(
        self,
        key: str,
        value: Any,
        expire: int = 3600,
        nx: bool = False,
    ) -> bool:
        """Set value in cache with optional expiration."""
        import time
        start = time.perf_counter()
        try:
            serialized = json.dumps(value, default=str)
            result = await self.client.set(key, serialized, ex=expire, nx=nx)
            REDIS_OPERATIONS.labels(operation="set", status="success").inc()
            return bool(result)
        except Exception as e:
            REDIS_OPERATIONS.labels(operation="set", status="error").inc()
            record_error("redis_set_error", "cache")
            raise
        finally:
            REDIS_OPERATION_DURATION.labels(operation="set").observe(time.perf_counter() - start)

    async def delete(self, *keys: str) -> int:
        """Delete keys from cache."""
        import time
        start = time.perf_counter()
        try:
            result = await self.client.delete(*keys)
            REDIS_OPERATIONS.labels(operation="delete", status="success").inc()
            return result
        except Exception as e:
            REDIS_OPERATIONS.labels(operation="delete", status="error").inc()
            record_error("redis_delete_error", "cache")
            raise
        finally:
            REDIS_OPERATION_DURATION.labels(operation="delete").observe(time.perf_counter() - start)

    async def exists(self, *keys: str) -> int:
        """Check if keys exist."""
        import time
        start = time.perf_counter()
        try:
            result = await self.client.exists(*keys)
            REDIS_OPERATIONS.labels(operation="exists", status="success").inc()
            return result
        except Exception as e:
            REDIS_OPERATIONS.labels(operation="exists", status="error").inc()
            record_error("redis_exists_error", "cache")
            raise
        finally:
            REDIS_OPERATION_DURATION.labels(operation="exists").observe(time.perf_counter() - start)

    async def incr(self, key: str, amount: int = 1) -> int:
        """Increment a counter."""
        import time
        start = time.perf_counter()
        try:
            result = await self.client.incrby(key, amount)
            REDIS_OPERATIONS.labels(operation="incr", status="success").inc()
            return result
        except Exception as e:
            REDIS_OPERATIONS.labels(operation="incr", status="error").inc()
            record_error("redis_incr_error", "cache")
            raise
        finally:
            REDIS_OPERATION_DURATION.labels(operation="incr").observe(time.perf_counter() - start)

    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on a key."""
        import time
        start = time.perf_counter()
        try:
            result = await self.client.expire(key, seconds)
            REDIS_OPERATIONS.labels(operation="expire", status="success").inc()
            return result
        except Exception as e:
            REDIS_OPERATIONS.labels(operation="expire", status="error").inc()
            record_error("redis_expire_error", "cache")
            raise
        finally:
            REDIS_OPERATION_DURATION.labels(operation="expire").observe(time.perf_counter() - start)

    async def keys(self, pattern: str) -> list[str]:
        """Find keys matching pattern."""
        import time
        start = time.perf_counter()
        try:
            result = await self.client.keys(pattern)
            REDIS_OPERATIONS.labels(operation="keys", status="success").inc()
            return result
        except Exception as e:
            REDIS_OPERATIONS.labels(operation="keys", status="error").inc()
            record_error("redis_keys_error", "cache")
            raise
        finally:
            REDIS_OPERATION_DURATION.labels(operation="keys").observe(time.perf_counter() - start)

    # High-level caching patterns
    async def get_or_set(
        self,
        key: str,
        factory,
        expire: int = 3600,
    ) -> Any:
        """Get from cache or compute and store."""
        value = await self.get(key)
        if value is not None:
            return value

        # Compute value
        if hasattr(factory, '__call__'):
            value = await factory() if hasattr(factory, '__await__') else factory()
        else:
            value = factory

        await self.set(key, value, expire=expire)
        return value

    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern."""
        keys = await self.keys(pattern)
        if keys:
            return await self.delete(*keys)
        return 0


# Global Redis manager
redis_manager = RedisManager()


async def get_redis() -> Redis:
    """Dependency for FastAPI to get Redis client."""
    return redis_manager.client


async def init_redis() -> None:
    """Initialize Redis on startup."""
    await redis_manager.initialize()


async def close_redis() -> None:
    """Close Redis on shutdown."""
    await redis_manager.close()


# Cache key builders
class CacheKeys:
    """Standardized cache key patterns."""

    # Bot execution cache
    BOT_EXECUTION = "cache:bot:{bot_id}:{input_hash}"
    BOT_METADATA = "cache:bot:meta:{bot_id}"

    # GraphRAG cache
    GRAPHRAG_QUERY = "cache:graphrag:{query_hash}"
    GRAPHRAG_ENTITIES = "cache:graphrag:entities:{entity_ids_hash}"

    # Hero bot registry
    HERO_BOTS_LIST = "cache:hero_bots:list"
    HERO_BOT_DETAIL = "cache:hero_bot:{bot_id}"

    # Freelance jobs
    FREELANCE_JOBS = "cache:freelance:jobs:{category}:{closer}"
    FREELANCE_CLOSERS = "cache:freelance:closers:{category}"

    # Client data
    CLIENT_INFO = "cache:client:{client_id}"
    CLIENT_QUOTA = "cache:client:quota:{client_id}"

    # Rate limiting
    RATE_LIMIT = "ratelimit:{key}"

    # Real estate
    REAL_ESTATE_LEADS = "cache:realestate:leads:{client_id}"

    @staticmethod
    def bot_execution(bot_id: str, input_hash: str) -> str:
        return f"cache:bot:{bot_id}:{input_hash}"

    @staticmethod
    def graphrag_query(query_hash: str) -> str:
        return f"cache:graphrag:{query_hash}"

    @staticmethod
    def freelance_jobs(category: Optional[str] = None, closer: Optional[str] = None) -> str:
        cat = category or "all"
        cl = closer or "all"
        return f"cache:freelance:jobs:{cat}:{cl}"

    @staticmethod
    def rate_limit(key: str) -> str:
        return f"ratelimit:{key}"