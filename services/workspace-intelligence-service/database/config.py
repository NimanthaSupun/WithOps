"""
Database configuration for Workspace Intelligence Service
"""
import os
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from .models import Base
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connection and session creation"""
    
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL", "").replace("postgresql://", "postgresql+asyncpg://")
        
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable is required")
        
        # Create async engine
        self.engine = create_async_engine(
            self.database_url,
            poolclass=NullPool,
            echo=False,
            future=True
        )
        
        # Create session factory
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        logger.info("Database manager initialized")
    
    async def create_tables(self, max_retries=3, retry_delay=2):
        """Create all tables with retry logic"""
        import asyncio
        
        for attempt in range(max_retries):
            try:
                async with self.engine.begin() as conn:
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
    
    @asynccontextmanager
    async def get_session(self):
        """Get a new async session"""
        session = None
        try:
            session = self.async_session()
            yield session
            await session.commit()
        except Exception as e:
            if session:
                await session.rollback()
            logger.error(f"Session error: {e}")
            raise
        finally:
            if session:
                await session.close()
    
    async def close(self):
        """Close the database engine"""
        await self.engine.dispose()
        logger.info("Database connection closed")


# Global instance
db_manager = DatabaseManager()


async def get_db_session():
    """Dependency for FastAPI routes"""
    async with db_manager.async_session() as session:
        yield session
