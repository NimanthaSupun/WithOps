"""
Database setup and migration script for DevSecOps application
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from database.config import db_manager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def setup_database():
    """Setup database tables and initial data"""
    
    print("🔧 Setting up DevSecOps database...")
    print("=" * 50)
    
    try:
        # Check if environment variables are set
        required_env_vars = [
            'SUPABASE_URL',
            'SUPABASE_ANON_KEY', 
            'SUPABASE_DATABASE_URL'
        ]
        
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        if missing_vars:
            print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
            print("Please set these in your .env file or environment")
            print("See .env.example for reference")
            return False
        
        print("✅ Environment variables configured")
        
        # Test database connection
        print("🔗 Testing database connection...")
        health_ok = await db_manager.health_check()
        if not health_ok:
            print("❌ Database connection failed")
            return False
        
        print("✅ Database connection successful")
        
        # Create tables
        print("📋 Creating database tables...")
        await db_manager.create_tables()
        print("✅ Database tables created successfully")
        
        print("\n🎉 Database setup completed successfully!")
        print("Your DevSecOps application is ready to use with Supabase")
        
        return True
        
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        logger.exception("Database setup error")
        return False

async def reset_database():
    """Reset database (drop and recreate all tables)"""
    
    print("⚠️  RESETTING DATABASE - ALL DATA WILL BE LOST!")
    print("=" * 50)
    
    confirm = input("Are you sure you want to reset the database? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Database reset cancelled")
        return False
    
    try:
        print("🗑️  Dropping all tables...")
        await db_manager.drop_tables()
        
        print("📋 Creating fresh tables...")
        await db_manager.create_tables()
        
        print("✅ Database reset completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Database reset failed: {e}")
        logger.exception("Database reset error")
        return False

async def check_database_status():
    """Check database connection and table status"""
    
    print("🔍 Checking database status...")
    print("=" * 30)
    
    try:
        # Check connection
        health_ok = await db_manager.health_check()
        if health_ok:
            print("✅ Database connection: OK")
        else:
            print("❌ Database connection: FAILED")
            return False
        
        # Check tables exist
        async with db_manager.get_session() as session:
            from sqlalchemy import text
            result = await session.execute(text("SELECT COUNT(*) FROM users"))
            user_count = result.scalar()
            print(f"✅ Users table: {user_count} records")
            
            result = await session.execute(text("SELECT COUNT(*) FROM organizations"))
            org_count = result.scalar()
            print(f"✅ Organizations table: {org_count} records")
            
            result = await session.execute(text("SELECT COUNT(*) FROM organization_installations"))
            install_count = result.scalar()
            print(f"✅ Installations table: {install_count} records")
        
        print("✅ Database status: HEALTHY")
        return True
        
    except Exception as e:
        print(f"❌ Database status check failed: {e}")
        logger.exception("Database status check error")
        return False

def main():
    """Main script entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="DevSecOps Database Management")
    parser.add_argument(
        'action', 
        choices=['setup', 'reset', 'status'],
        help='Action to perform'
    )
    
    args = parser.parse_args()
    
    if args.action == 'setup':
        success = asyncio.run(setup_database())
    elif args.action == 'reset':
        success = asyncio.run(reset_database())
    elif args.action == 'status':
        success = asyncio.run(check_database_status())
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
