"""
Database configuration and connection management for Threat Modeling Service
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
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
        # Database URL from environment
        self.database_url = os.getenv('DATABASE_URL', 'sqlite+aiosqlite:///./threat_modeling.db')
        
        # Check if using SQLite
        self.using_sqlite = self.database_url.startswith('sqlite')
        
        if self.using_sqlite:
            logger.warning("Using SQLite database")
            async_url = self.database_url
            sync_url = self.database_url.replace('sqlite+aiosqlite://', 'sqlite:///')
            engine_kwargs = {
                "echo": False,
                "connect_args": {"check_same_thread": False}
            }
        else:
            # PostgreSQL configuration
            async_url = self.database_url.replace('postgresql://', 'postgresql+asyncpg://')
            sync_url = self.database_url
            
            connect_args = {
                "command_timeout": 60,
                "server_settings": {
                    "statement_timeout": "45s",
                    "idle_in_transaction_session_timeout": "120s"
                }
            }
            
            engine_kwargs = {
                "echo": False,
                "pool_size": 5,
                "max_overflow": 10,
                "pool_recycle": 600,
                "pool_pre_ping": True,
                "pool_timeout": 45,
                "connect_args": connect_args
            }
        
        # Async engine
        self.async_engine = create_async_engine(async_url, **engine_kwargs)
        
        # Async session factory
        self.AsyncSessionLocal = async_sessionmaker(
            bind=self.async_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Sync engine for migrations
        if self.using_sqlite:
            self.sync_engine = create_engine(
                sync_url,
                echo=False,
                connect_args={"check_same_thread": False}
            )
        else:
            self.sync_engine = create_engine(
                sync_url,
                echo=False,
                pool_size=5,
                max_overflow=10,
            )
        
        # Sync session factory
        self.SessionLocal = sessionmaker(bind=self.sync_engine)
    
    async def create_tables(self, max_retries=3, retry_delay=2):
        """Create all tables with retry logic"""
        import asyncio
        
        for attempt in range(max_retries):
            try:
                async with self.async_engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)
                logger.info("✅ Database tables created successfully")
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"⚠️ Database connection attempt {attempt + 1}/{max_retries} failed: {e}. Retrying in {retry_delay}s...")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"❌ Failed to create tables after {max_retries} attempts: {e}")
                    raise
    
    async def drop_tables(self):
        """Drop all tables"""
        async with self.async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.info("🗑️ Database tables dropped")
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get async database session"""
        session = None
        try:
            session = self.AsyncSessionLocal()
            yield session
            await session.commit()
        except Exception as e:
            if session:
                try:
                    await session.rollback()
                except Exception as rollback_error:
                    logger.error(f"Failed to rollback session: {rollback_error}")
            
            logger.error(f"Database session error: {e}")
            raise
        finally:
            if session:
                try:
                    await session.close()
                except Exception as close_error:
                    logger.error(f"Failed to close session: {close_error}")
    
    def get_sync_session(self) -> Session:
        """Get sync database session (for migrations)"""
        return self.SessionLocal()
    
    async def health_check(self) -> bool:
        """Check database connection health"""
        try:
            async with self.get_session() as session:
                await session.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


# Global database manager instance
db_manager = DatabaseManager()


# FastAPI dependency
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions"""
    async with db_manager.get_session() as session:
        yield session
