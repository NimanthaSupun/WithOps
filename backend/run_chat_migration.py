#!/usr/bin/env python3
"""
Run database migration for chat conversations
"""
import asyncio
import asyncpg
import os
import sys
from pathlib import Path

# Supabase connection details
SUPABASE_CONFIG = {
    "host": "aws-0-ap-south-1.pooler.supabase.com",
    "port": 5432,
    "database": "postgres",
    "user": "postgres.fcmcsbmsntmpeyjltqbi",
    "password": os.getenv("SUPABASE_DB_PASSWORD", "5m19NTF6y0x1fJgr")
}

async def run_migration():
    """Run the chat conversations migration"""
    try:
        print("🗃️ Connecting to Supabase database...")
        conn = await asyncpg.connect(**SUPABASE_CONFIG)
        
        # Read migration file
        migration_file = Path(__file__).parent / "migrations" / "020_add_chat_conversations.sql"
        print(f"📄 Reading migration: {migration_file}")
        
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        # Execute migration
        print("⚙️ Executing migration...")
        await conn.execute(migration_sql)
        
        print("✅ Migration completed successfully!")
        
        # Verify tables exist
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('chat_conversations', 'chat_messages')
            ORDER BY table_name
        """)
        
        print("\n📊 Created tables:")
        for table in tables:
            print(f"  ✓ {table['table_name']}")
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(run_migration())
    sys.exit(0 if success else 1)
