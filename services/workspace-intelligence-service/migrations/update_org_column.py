"""
Migration: Update repository_trees to use organization_name instead of organization_id
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def migrate():
    database_url = os.getenv("DATABASE_URL", "")
    
    # Parse the URL manually for asyncpg
    import re
    match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', database_url)
    if not match:
        print(f"❌ Invalid DATABASE_URL format: {database_url}")
        return
    
    user, password, host, port, database = match.groups()
    
    conn = await asyncpg.connect(
        user=user,
        password=password,
        host=host,
        port=int(port),
        database=database
    )
    
    try:
        # Check if organization_name column exists
        check_column = await conn.fetchval("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'repository_trees' 
            AND column_name = 'organization_name'
        """)
        
        if check_column:
            print("✅ organization_name column already exists")
            return
        
        # Add organization_name column
        await conn.execute("""
            ALTER TABLE repository_trees 
            ADD COLUMN IF NOT EXISTS organization_name VARCHAR
        """)
        print("✅ Added organization_name column")
        
        # Copy data from organization_id to organization_name (use org login instead of ID)
        # This requires joining with organizations table if it exists
        # For now, we'll just set it to empty and let the service populate it
        await conn.execute("""
            UPDATE repository_trees 
            SET organization_name = ''
            WHERE organization_name IS NULL
        """)
        print("✅ Initialized organization_name values")
        
        # Make organization_name NOT NULL
        await conn.execute("""
            ALTER TABLE repository_trees 
            ALTER COLUMN organization_name SET NOT NULL
        """)
        print("✅ Set organization_name as NOT NULL")
        
        print("✅ Migration completed successfully")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(migrate())
