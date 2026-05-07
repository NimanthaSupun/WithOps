#!/usr/bin/env python3
"""
Initialize local SQLite database for development
"""
import asyncio
import sys
import os
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from database.config import db_manager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def init_database():
    """Initialize the local SQLite database"""
    try:
        logger.info("🗃️ Initializing local SQLite database...")
        
        # Create all tables
        await db_manager.create_tables()
        
        # Test the connection
        health_ok = await db_manager.health_check()
        if health_ok:
            logger.info("✅ Database initialized successfully!")
            logger.info(f"📂 Database file location: {os.path.abspath('devsecops.db')}")
        else:
            logger.error("❌ Database health check failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        return False
    
    return True

async def main():
    """Main function"""
    logger.info("🚀 DevSecOps Database Initialization")
    logger.info("=" * 50)
    
    success = await init_database()
    
    if success:
        logger.info("🎉 Database setup complete! You can now start the backend server.")
    else:
        logger.error("💥 Database setup failed. Please check the logs above.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())