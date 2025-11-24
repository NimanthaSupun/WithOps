"""
Migration: Add linked_users field to organization_installations
Date: 2025-11-19
Description: Enable multi-user access to installations by adding linked_users JSON array
"""

import asyncio
from database.config import db_manager
from sqlalchemy import text

async def migrate():
    """Add linked_users column to organization_installations table"""
    async with db_manager.get_session() as session:
        try:
            # Add linked_users column with default empty array
            await session.execute(text("""
                ALTER TABLE organization_installations 
                ADD COLUMN IF NOT EXISTS linked_users JSONB DEFAULT '[]'::jsonb
            """))
            
            # Initialize existing rows with empty array
            await session.execute(text("""
                UPDATE organization_installations 
                SET linked_users = '[]'::jsonb 
                WHERE linked_users IS NULL
            """))
            
            await session.commit()
            print("✅ Migration completed successfully")
            print("   - Added linked_users column to organization_installations")
            print("   - Initialized existing rows with empty array")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Migration failed: {e}")
            raise

async def rollback():
    """Remove linked_users column"""
    async with db_manager.get_session() as session:
        try:
            await session.execute(text("""
                ALTER TABLE organization_installations 
                DROP COLUMN IF EXISTS linked_users
            """))
            
            await session.commit()
            print("✅ Rollback completed successfully")
            print("   - Removed linked_users column from organization_installations")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Rollback failed: {e}")
            raise

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        print("🔄 Rolling back migration: add_linked_users")
        asyncio.run(rollback())
    else:
        print("🚀 Running migration: add_linked_users")
        asyncio.run(migrate())
