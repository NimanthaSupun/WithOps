"""
Add missing columns to project_analyses table
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

async def migrate():
    """Add user_id and organization_name columns to project_analyses"""
    
    # Parse connection string
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        print("Adding columns to project_analyses table...")
        
        # Add user_id column
        try:
            await conn.execute("""
                ALTER TABLE project_analyses 
                ADD COLUMN IF NOT EXISTS user_id VARCHAR NOT NULL DEFAULT 'system';
            """)
            print("✅ Added user_id column")
        except Exception as e:
            print(f"⚠️  user_id column: {e}")
        
        # Add organization_name column
        try:
            await conn.execute("""
                ALTER TABLE project_analyses 
                ADD COLUMN IF NOT EXISTS organization_name VARCHAR NOT NULL DEFAULT 'Unknown';
            """)
            print("✅ Added organization_name column")
        except Exception as e:
            print(f"⚠️  organization_name column: {e}")
        
        # Create indexes
        try:
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_project_analyses_user_id 
                ON project_analyses(user_id);
            """)
            print("✅ Created index on user_id")
        except Exception as e:
            print(f"⚠️  Index on user_id: {e}")
        
        try:
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_project_analyses_org_name 
                ON project_analyses(organization_name);
            """)
            print("✅ Created index on organization_name")
        except Exception as e:
            print(f"⚠️  Index on organization_name: {e}")
        
        # Verify columns exist
        result = await conn.fetch("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'project_analyses'
            ORDER BY ordinal_position;
        """)
        
        print("\n📊 Current columns in project_analyses:")
        for row in result:
            print(f"  - {row['column_name']}: {row['data_type']} (nullable: {row['is_nullable']})")
        
        print("\n✅ Migration completed successfully!")
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(migrate())
