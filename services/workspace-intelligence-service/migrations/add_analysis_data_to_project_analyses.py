"""
Migration: Add analysis_data column to project_analyses table
This column will store the complete project analysis including repositories and findings
"""

from sqlalchemy import text
import asyncio
from database.config import db_manager


async def run_migration():
    """Add analysis_data JSON column to project_analyses table"""
    
    async with db_manager.get_session() as session:
        try:
            print("🔄 Adding analysis_data column to project_analyses table...")
            
            # Check if column already exists
            check_sql = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'project_analyses' 
                AND column_name = 'analysis_data'
            """)
            
            result = await session.execute(check_sql)
            existing = result.fetchone()
            
            if existing:
                print("✅ Column 'analysis_data' already exists, skipping migration")
                return
            
            # Add the column
            alter_sql = text("""
                ALTER TABLE project_analyses 
                ADD COLUMN IF NOT EXISTS analysis_data JSONB
            """)
            
            await session.execute(alter_sql)
            await session.commit()
            
            print("✅ Successfully added analysis_data column to project_analyses table")
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            await session.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(run_migration())
