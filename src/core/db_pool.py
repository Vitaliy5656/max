"""
SQLite Connection Pool for MAX
Provides connection pooling with leak detection and timeout protection.
"""
import asyncio
import aiosqlite
import time
import logging
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)


class SQLitePool:
    """
    Connection pool for SQLite with leak detection.
    
    Features:
    - Connection pooling for concurrent access
    - Timeout protection (prevents deadlocks)
    - Leak detection (monitors long-held connections)
    - WAL mode for better concurrency
    """
    
    def __init__(self, db_path: Path, pool_size: int = 10):
        self._pool: asyncio.Queue = asyncio.Queue(maxsize=pool_size)
        self._db_path = db_path
        self._pool_size = pool_size
        self._acquired = {}  # conn -> acquisition time
        self._initialized = False
    
    async def initialize(self):
        """Initialize connection pool."""
        if self._initialized:
            return
        
        log.info(f"Initializing DB pool: {self._pool_size} connections")
        
        for _ in range(self._pool_size):
            conn = await aiosqlite.connect(
                str(self._db_path),
                timeout=60.0
            )
            conn.row_factory = aiosqlite.Row
            # Enable WAL mode for better concurrency
            await conn.execute("PRAGMA journal_mode=WAL")
            await conn.execute("PRAGMA busy_timeout=30000")  # 30s timeout
            await self._pool.put(conn)
        
        self._initialized = True
        
        # Start leak monitor
        asyncio.create_task(self._leak_monitor())
        
        log.info(f"✅ DB pool initialized: {self._pool_size} connections")
    
    async def acquire(self, timeout: float = 30.0):
        """
        Acquire a connection from pool.
        
        Args:
            timeout: Maximum time to wait for connection (seconds)
            
        Returns:
            Database connection
            
        Raises:
            RuntimeError: If pool exhausted or timeout
        """
        try:
            conn = await asyncio.wait_for(
                self._pool.get(),
                timeout=timeout
            )
            self._acquired[id(conn)] = time.time()
            return conn
        except asyncio.TimeoutError:
            log.error("⚠️ DB pool exhausted! Possible connection leak")
            raise RuntimeError("DB pool exhausted! Possible connection leak")
    
    async def release(self, conn):
        """Release connection back to pool."""
        conn_id = id(conn)
        if conn_id in self._acquired:
            del self._acquired[conn_id]
        await self._pool.put(conn)
    
    async def _leak_monitor(self):
        """Monitor for connection leaks (connections held > 5 minutes)."""
        while True:
            await asyncio.sleep(60)  # Check every minute
            
            now = time.time()
            for conn_id, acquired_at in list(self._acquired.items()):
                held_time = now - acquired_at
                if held_time > 300:  # 5 minutes
                    log.warning(
                        f"⚠️ Connection leak detected! "
                        f"Connection held for {held_time:.0f}s"
                    )
    
    async def close(self):
        """Close all connections in pool."""
        log.info("Closing DB pool...")
        
        # Close all pooled connections
        while not self._pool.empty():
            try:
                conn = await asyncio.wait_for(self._pool.get(), timeout=1.0)
                await conn.close()
            except asyncio.TimeoutError:
                break
        
        log.info("✅ DB pool closed")
    
    def get_stats(self) -> dict:
        """Get pool statistics."""
        return {
            "pool_size": self._pool_size,
            "available": self._pool.qsize(),
            "acquired": len(self._acquired),
            "initialized": self._initialized
        }


# Global pool instance
_global_pool: Optional[SQLitePool] = None


async def get_db_pool() -> SQLitePool:
    """Get global DB pool instance."""
    global _global_pool
    
    if _global_pool is None:
        from src.core.config import Config
        config = Config()
        _global_pool = SQLitePool(
            db_path=Path(config.db_path),
            pool_size=10
        )
        await _global_pool.initialize()
    
    return _global_pool


class DBConnection:
    """Context manager for DB connections."""
    
    def __init__(self, pool: SQLitePool):
        self.pool = pool
        self.conn = None
    
    async def __aenter__(self):
        self.conn = await self.pool.acquire()
        return self.conn
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            await self.pool.release(self.conn)


# Usage example:
# async with DBConnection(pool) as conn:
#     async with conn.execute("SELECT * FROM table") as cursor:
#         rows = await cursor.fetchall()
