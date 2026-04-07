"""
Database configuration for Pipeline Prediction Service
"""
import os
import logging
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from .models import Base

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages database connection and session creation for asynchronous SQLAlchemy"""
    
    def __init__(self):
        # Database URL with asyncpg driver
        self.database_url = os.getenv("DATABASE_URL", "").replace("postgresql://", "postgresql+asyncpg://")
        
        if not self.database_url:
            # Fallback for local development if .env is missing or DATABASE_URL not set
            logger.warning("⚠️ DATABASE_URL not set. Falling back to default (might fail if not provided in env).")
            # In a real environment, this should probably raise an error
        
        # Create async engine with NullPool to allow external connection pooling (like Supabase/PgBouncer)
        self.engine = create_async_engine(
            self.database_url,
            poolclass=NullPool,
            echo=False, # Set to True for SQL debugging
            future=True
        )
        
        # Create session factory
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        logger.info("✅ Database manager initialized")
    
    async def create_tables(self, max_retries=3, retry_delay=2):
        """Create all tables defined in models.py with retry logic"""
        import asyncio
        for attempt in range(max_retries):
            try:
                # Use engine.begin() for automatic transaction management
                async with self.engine.begin() as conn:
                    # run_sync is required to use metadata.create_all with an async engine
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
        """
        Context manager for getting a new async database session.
        Usage: 
            async with db_manager.get_session() as session:
                # ... use session
        """
        session = None
        try:
            session = self.async_session()
            yield session
            # Automatic commit on context exit if no exception occurred
            await session.commit()
        except Exception as e:
            if session:
                # Rollback on error
                await session.rollback()
            logger.error(f"❌ Session error: {e}")
            raise
        finally:
            if session:
                # Always close the session
                await session.close()
    
    async def close(self):
        """Cleanly dispose of the database engine"""
        await self.engine.dispose()
        logger.info("Database connection closed")

# Global instance for use across the application
db_manager = DatabaseManager()

async def get_db_session():
    """
    FastAPI dependency that provides an async session for routes.
    """
    async with db_manager.async_session() as session:
        yield session
