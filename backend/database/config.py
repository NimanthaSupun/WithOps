"""
Supabase database configuration and connection management
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import logging

from .models import Base

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

class SupabaseConfig:
    """Supabase configuration"""
    
    def __init__(self):
        # Supabase credentials from environment
        self.url = os.getenv('SUPABASE_URL')
        self.key = os.getenv('SUPABASE_ANON_KEY')
        self.service_role_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

        # Database URL priority: LOCAL_DATABASE_URL > SUPABASE_DATABASE_URL > SQLite fallback
        self.database_url = (
            os.getenv('LOCAL_DATABASE_URL') or 
            os.getenv('SUPABASE_DATABASE_URL') or 
            "sqlite+aiosqlite:///./devsecops.db"
        )
        
        # Check if we're using SQLite fallback
        self.using_sqlite = self.database_url.startswith('sqlite')
        
        if self.using_sqlite:
            logger.warning("Using SQLite fallback database. Some features may be limited.")
        elif not all([self.url, self.key]):
            logger.warning("Missing Supabase configuration. Using SQLite fallback database.")
            self.database_url = "sqlite+aiosqlite:///./devsecops.db"
            self.using_sqlite = True
    
    def get_client(self, use_service_role: bool = False) -> Client:
        """Get Supabase client"""
        key = self.service_role_key if use_service_role else self.key
        if not key:
            raise ValueError("Missing service role key for admin operations")
        return create_client(self.url, key)


class DatabaseManager:
    """Database connection and session management"""
    
    def __init__(self):
        self.config = SupabaseConfig()
        
        # Prepare database URL for async operations
        if self.config.using_sqlite:
            # SQLite configuration
            async_url = self.config.database_url
            sync_url = self.config.database_url.replace('sqlite+aiosqlite://', 'sqlite:///')
            engine_kwargs = {
                "echo": False,
                "connect_args": {"check_same_thread": False}
            }
        else:
            # PostgreSQL configuration with enhanced timeout settings for Supabase
            async_url = self.config.database_url.replace('postgresql://', 'postgresql+asyncpg://')
            sync_url = self.config.database_url
            
            # Add connection arguments for better reliability and Supabase pooler compatibility
            connect_args = {
                "command_timeout": 60,      # Increased command timeout (60 seconds)
                "server_settings": {
                    "statement_timeout": "45s",   # SQL statement timeout
                    "idle_in_transaction_session_timeout": "120s"  # Longer idle timeout
                },
                # SSL configuration for Supabase
                "ssl": "require"
            }
            
            engine_kwargs = {
                "echo": False,
                "pool_size": 2,             # Smaller pool size for Supabase pooler
                "max_overflow": 3,          # Reduced overflow for stability
                "pool_recycle": 600,        # Recycle connections every 10 minutes
                "pool_pre_ping": True,      # Verify connections before use
                "pool_timeout": 45,         # Connection acquisition timeout
                "connect_args": connect_args
            }
        
        # Async engine for main operations
        self.async_engine = create_async_engine(async_url, **engine_kwargs)
        
        # Async session factory
        self.AsyncSessionLocal = async_sessionmaker(
            bind=self.async_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Sync engine for migrations and setup
        if self.config.using_sqlite:
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
    
    async def create_tables(self):
        """Create all tables"""
        async with self.async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    
    async def drop_tables(self):
        """Drop all tables (for testing/reset)"""
        async with self.async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.info("Database tables dropped")
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get async database session with improved error handling"""
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
            
            # More specific error logging
            if "Connect call failed" in str(e) or "Connection refused" in str(e):
                logger.error(f"Database connection failed: {e}. Consider using SQLite fallback.")
            else:
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
            from sqlalchemy import text
            async with self.get_session() as session:
                await session.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


# Global database manager instance
db_manager = DatabaseManager()

# Dependency for FastAPI
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions"""
    async with db_manager.get_session() as session:
        yield session

# Supabase client for real-time and auth features
def get_supabase_client(use_service_role: bool = False) -> Client:
    """Get Supabase client for real-time features"""
    return db_manager.config.get_client(use_service_role)
