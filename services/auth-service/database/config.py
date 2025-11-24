"""
Database configuration for Auth Service
Uses the same database setup as other services
"""

import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import logging

from .models import Base

load_dotenv()

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Database connection and session management"""
    
    def __init__(self):
        # Get database URL from environment
        database_url = os.getenv('DATABASE_URL', 'sqlite+aiosqlite:///./auth.db')
        
        # Check if using SQLite
        self.using_sqlite = database_url.startswith('sqlite')
        
        if self.using_sqlite:
            logger.warning("Using SQLite fallback database")
            async_url = database_url
            engine_kwargs = {
                "echo": False,
                "connect_args": {"check_same_thread": False}
            }
        else:
            # PostgreSQL configuration
            async_url = database_url.replace('postgresql://', 'postgresql+asyncpg://')
            
            connect_args = {
                "command_timeout": 60,
                "server_settings": {
                    "statement_timeout": "45s",
                    "idle_in_transaction_session_timeout": "120s"
                },
                "ssl": "require"
            }
            
            engine_kwargs = {
                "echo": False,
                "pool_size": 2,
                "max_overflow": 3,
                "pool_recycle": 600,
                "pool_pre_ping": True,
                "pool_timeout": 45,
                "connect_args": connect_args
            }
        
        # Create async engine
        self.async_engine = create_async_engine(async_url, **engine_kwargs)
        
        # Create async session factory
        self.async_session_factory = async_sessionmaker(
            self.async_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        logger.info(f"Database configured: {'SQLite' if self.using_sqlite else 'PostgreSQL'}")
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get async database session"""
        async with self.async_session_factory() as session:
            try:
                yield session
            except Exception as e:
                await session.rollback()
                logger.error(f"Database session error: {e}")
                raise
            finally:
                await session.close()
    
    async def create_tables(self, max_retries=3, retry_delay=2):
        """Create database tables with retry logic"""
        import asyncio
        
        for attempt in range(max_retries):
            try:
                async with self.async_engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)
                logger.info("Database tables created")
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"⚠️ Database connection attempt {attempt + 1}/{max_retries} failed: {e}. Retrying in {retry_delay}s...")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"❌ Failed to create tables after {max_retries} attempts: {e}")
                    raise
    
    async def close(self):
        """Close database connections"""
        await self.async_engine.dispose()
        logger.info("Database connections closed")


# Global database manager instance
db_manager = DatabaseManager()


# FastAPI dependency
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions"""
    async with db_manager.get_session() as session:
        yield session
