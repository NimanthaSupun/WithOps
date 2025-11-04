#!/usr/bin/env python3
"""
Simple database connection test script
"""
import asyncio
import sys
import os
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from database.config import db_manager
from sqlalchemy import text

async def test_database_connection():
    """Test the database connection"""
    try:
        print("🔍 Testing database connection...")
        
        async with db_manager.get_session() as session:
            # Simple connectivity test
            result = await session.execute(text("SELECT 1 as test"))
            test_value = result.scalar()
            
            if test_value == 1:
                print("✅ Database connection successful!")
                print(f"📊 Using database: {db_manager.database_url}")
                return True
            else:
                print("❌ Database connection failed - unexpected result")
                return False
                
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print(f"🔗 Database URL: {db_manager.database_url}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_database_connection())
    sys.exit(0 if success else 1)