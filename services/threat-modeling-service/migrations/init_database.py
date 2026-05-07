"""
Database initialization script
Creates all tables for threat modeling service
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from database.config import db_manager


async def init_database():
    """Initialize database tables"""
    print("🔧 Initializing Threat Modeling Service database...")
    
    try:
        await db_manager.create_tables()
        print("✅ Database tables created successfully!")
        
        # Verify tables
        health = await db_manager.health_check()
        if health:
            print("✅ Database connection verified")
        else:
            print("⚠️  Database connection issue")
            
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(init_database())
