"""
Database Configuration for AI RAG Service
"""

import os
from typing import Optional
import asyncpg
import logging

logger = logging.getLogger(__name__)


class DatabaseConfig:
    """Database configuration and connection management"""
    
    def __init__(self):
        self.host = os.getenv("SUPABASE_DB_HOST", "aws-0-ap-south-1.pooler.supabase.com")
        self.port = int(os.getenv("SUPABASE_DB_PORT", "5432"))
        self.database = os.getenv("SUPABASE_DB_NAME", "postgres")
        self.user = os.getenv("SUPABASE_DB_USER", "postgres.fcmcsbmsntmpeyjltqbi")
        self.password = os.getenv("SUPABASE_DB_PASSWORD", "5m19NTF6y0x1fJgr")
        self._pool: Optional[asyncpg.Pool] = None
    
    async def initialize(self):
        """Initialize database connection pool"""
        try:
            self._pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                min_size=2,
                max_size=10,
                command_timeout=60
            )
            logger.info(f"✅ Database pool initialized: {self.host}:{self.port}/{self.database}")
        except Exception as e:
            logger.error(f"❌ Failed to initialize database pool: {str(e)}")
            raise
    
    async def close(self):
        """Close database connection pool"""
        if self._pool:
            await self._pool.close()
            logger.info("Database pool closed")
    
    async def get_connection(self):
        """Get a database connection from the pool"""
        if not self._pool:
            raise RuntimeError("Database pool not initialized")
        return await self._pool.acquire()
    
    async def release_connection(self, connection):
        """Release a database connection back to the pool"""
        if self._pool:
            await self._pool.release(connection)


# Global database config instance
db_config = DatabaseConfig()
