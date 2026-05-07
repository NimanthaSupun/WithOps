"""
Database configuration for Workflow Orchestration Service
Handles Supabase PostgreSQL connection and session management
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
        # Database URL from environment
        self.database_url = os.getenv('DATABASE_URL')
        
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable is required")
        
        # Convert postgres:// to postgresql+asyncpg:// for async
        if self.database_url.startswith('postgres://'):
            self.database_url = self.database_url.replace('postgres://', 'postgresql+asyncpg://', 1)
        elif self.database_url.startswith('postgresql://'):
            self.database_url = self.database_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
        
        # Create async engine
        self.engine = create_async_engine(
            self.database_url,
            echo=os.getenv('ENVIRONMENT') == 'development',
            pool_pre_ping=True,
            pool_size=20,
            max_overflow=40
        )
        
        # Create async session factory
        self.async_session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        logger.info("✅ Database manager initialized")
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get async database session"""
        async with self.async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"❌ Database session error: {e}")
                raise
            finally:
                await session.close()
    
    async def create_schema(self):
        """Create workflow_orchestration schema if it doesn't exist"""
        async with self.engine.begin() as conn:
            await conn.execute("CREATE SCHEMA IF NOT EXISTS workflow_orchestration")
            logger.info("✅ Schema 'workflow_orchestration' created/verified")
    
    async def create_tables(self):
        """Create all tables"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("✅ All tables created/verified")
    
    async def drop_tables(self):
        """Drop all tables (use with caution!)"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            logger.warning("⚠️ All tables dropped")
    
    async def close(self):
        """Close database connections"""
        await self.engine.dispose()
        logger.info("🔌 Database connections closed")


# Global database manager instance
db_manager = DatabaseManager()
