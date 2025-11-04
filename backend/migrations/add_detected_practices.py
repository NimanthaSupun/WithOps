"""
Migration: Add detected_practices column to project_analyses table
"""

import asyncio
from sqlalchemy import text
from database.config import db_manager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def add_detected_practices_column():
    """Add detected_practices JSON column to project_analyses table"""
    
    async with db_manager.get_session() as session:
        try:
            # Check if column exists
            check_sql = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='project_analyses' 
                AND column_name='detected_practices'
            """)
            
            result = await session.execute(check_sql)
            exists = result.fetchone()
            
            if exists:
                logger.info("✅ Column 'detected_practices' already exists")
                return
            
            # Add the column
            alter_sql = text("""
                ALTER TABLE project_analyses 
                ADD COLUMN detected_practices JSONB
            """)
            
            await session.execute(alter_sql)
            await session.commit()
            
            logger.info("✅ Successfully added 'detected_practices' column")
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            await session.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(add_detected_practices_column())
