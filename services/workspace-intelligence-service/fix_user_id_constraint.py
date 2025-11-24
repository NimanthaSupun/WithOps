"""
Remove foreign key constraint from project_analyses.user_id
Make it nullable since we use 'system' for unauthenticated requests
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

async def fix_constraint():
    """Remove foreign key constraint and make user_id nullable"""
    
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        print("Checking for foreign key constraint...")
        
        # Get constraint name
        constraints = await conn.fetch("""
            SELECT constraint_name
            FROM information_schema.table_constraints
            WHERE table_name = 'project_analyses'
            AND constraint_type = 'FOREIGN KEY'
            AND constraint_name LIKE '%user_id%';
        """)
        
        print(f"Found {len(constraints)} user_id foreign key constraints:")
        for c in constraints:
            print(f"  - {c['constraint_name']}")
        
        # Drop foreign key constraints
        for c in constraints:
            constraint_name = c['constraint_name']
            print(f"\nDropping constraint: {constraint_name}")
            await conn.execute(f"""
                ALTER TABLE project_analyses 
                DROP CONSTRAINT IF EXISTS {constraint_name};
            """)
            print(f"✅ Dropped {constraint_name}")
        
        # Make user_id nullable
        print("\nMaking user_id column nullable...")
        await conn.execute("""
            ALTER TABLE project_analyses 
            ALTER COLUMN user_id DROP NOT NULL;
        """)
        print("✅ user_id is now nullable")
        
        # Verify
        result = await conn.fetchrow("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'project_analyses'
            AND column_name = 'user_id';
        """)
        
        print(f"\n📊 user_id column: {result['data_type']}, nullable: {result['is_nullable']}")
        
        print("\n✅ Migration completed successfully!")
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(fix_constraint())
