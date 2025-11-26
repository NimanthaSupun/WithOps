"""
Database initialization script for Workflow Orchestration Service
Creates the schema and tables in Supabase PostgreSQL
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent))

from database.config import db_manager
from database.models import Base
from sqlalchemy import text


async def create_schema():
    """Create workflow_orchestration schema"""
    print("🔧 Creating schema...")
    
    async with db_manager.engine.begin() as conn:
        # Create schema if not exists
        await conn.execute(text(
            "CREATE SCHEMA IF NOT EXISTS workflow_orchestration"
        ))
        print("✅ Schema 'workflow_orchestration' created")


async def create_tables():
    """Create all tables"""
    print("🔧 Creating tables...")
    
    async with db_manager.engine.begin() as conn:
        # Create all tables defined in models
        await conn.run_sync(Base.metadata.create_all)
    
    print("✅ Tables created:")
    print("  - workflow_trees")
    print("  - workflow_executions")
    print("  - workflow_security_scans")
    print("  - workflow_canvas_designs")
    print("  - workflow_metrics")


async def verify_tables():
    """Verify tables were created"""
    print("\n🔍 Verifying tables...")
    
    async with db_manager.get_session() as session:
        result = await session.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'workflow_orchestration'
            ORDER BY table_name
        """))
        
        tables = result.fetchall()
        if tables:
            print("✅ Found tables:")
            for table in tables:
                print(f"  - {table[0]}")
        else:
            print("❌ No tables found in workflow_orchestration schema")


async def init_database():
    """Initialize database schema and tables"""
    print("=" * 60)
    print("Workflow Orchestration Service - Database Initialization")
    print("=" * 60)
    print()
    
    # Check database URL
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("❌ ERROR: DATABASE_URL environment variable not set")
        print("Please set DATABASE_URL in .env file")
        return False
    
    print(f"📦 Database: {db_url.split('@')[1] if '@' in db_url else 'configured'}")
    print()
    
    try:
        # Create schema
        await create_schema()
        print()
        
        # Create tables
        await create_tables()
        print()
        
        # Verify
        await verify_tables()
        print()
        
        print("=" * 60)
        print("✅ Database initialization completed successfully!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ Database initialization failed: {str(e)}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return False


async def drop_tables():
    """Drop all tables (use with caution!)"""
    print("⚠️  WARNING: This will drop all tables in workflow_orchestration schema!")
    
    confirm = input("Type 'YES' to confirm: ")
    if confirm != 'YES':
        print("Cancelled.")
        return
    
    print("🔧 Dropping tables...")
    
    async with db_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    print("✅ Tables dropped")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Database management for Workflow Orchestration Service")
    parser.add_argument(
        'action',
        choices=['init', 'verify', 'drop'],
        help='Action to perform: init (create schema and tables), verify (check tables), drop (remove all tables)'
    )
    
    args = parser.parse_args()
    
    if args.action == 'init':
        asyncio.run(init_database())
    elif args.action == 'verify':
        asyncio.run(verify_tables())
    elif args.action == 'drop':
        asyncio.run(drop_tables())
