"""
Migration script to make project_id nullable for unified analyses
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.config import DatabaseManager
from sqlalchemy import text


async def run_migration():
    """Run the migration to make project_id nullable"""
    print("🔄 Starting migration: Make project_id nullable...")
    
    db_manager = DatabaseManager()
    
    try:
        async with db_manager.get_session() as session:
            # Read and execute the SQL migration
            sql_file = Path(__file__).parent / "make_project_id_nullable.sql"
            with open(sql_file, 'r') as f:
                sql_content = f.read()
            
            print(f"📝 Executing SQL:\n{sql_content}")
            await session.execute(text(sql_content))
            await session.commit()
            
            print("✅ Migration completed successfully!")
            print("   project_id column is now nullable in project_analyses table")
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(run_migration())
