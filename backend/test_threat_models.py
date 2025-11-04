#!/usr/bin/env python3
"""
Test threat modeling database queries specifically
"""
import asyncio
import time
import sys
import os

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.config import db_manager
from database.models import ThreatModel
from sqlalchemy import select, func, text

async def test_threat_model_queries():
    """Test threat modeling related database operations"""
    print("🔍 Testing threat modeling database queries...")
    
    try:
        async with db_manager.get_session() as session:
            print("✅ Database session created successfully")
            
            # Test if ThreatModel table exists
            try:
                print("🔍 Testing ThreatModel table existence...")
                start_time = time.time()
                
                # First, test if the table exists with a simple count
                result = await session.execute(select(func.count(ThreatModel.id)))
                count = result.scalar()
                elapsed = time.time() - start_time
                
                print(f"✅ ThreatModel table exists with {count} records ({elapsed:.2f}s)")
                
            except Exception as e:
                print(f"❌ ThreatModel table issue: {e}")
                # Try to check if the table exists in the database
                try:
                    result = await session.execute(text("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'threat_models')"))
                    exists = result.scalar()
                    print(f"   Table exists in schema: {exists}")
                except Exception as schema_e:
                    print(f"   Schema check failed: {schema_e}")
                return
            
            # Test the actual query from the endpoint
            print("🔍 Testing the exact query from /models endpoint...")
            start_time = time.time()
            
            try:
                result = await session.execute(
                    select(ThreatModel).order_by(ThreatModel.created_at.desc())
                )
                models = result.scalars().all()
                elapsed = time.time() - start_time
                
                print(f"✅ Models query completed: {len(models)} models ({elapsed:.2f}s)")
                
                # Show some details if we have models
                if models:
                    print("   Sample models:")
                    for i, model in enumerate(models[:3]):  # Show first 3
                        print(f"   - {model.name} (ID: {model.id}, Status: {model.status})")
                        if i >= 2:  # Limit to first 3
                            break
                else:
                    print("   No threat models found in database")
                    
            except Exception as query_e:
                elapsed = time.time() - start_time
                print(f"❌ Models query failed after {elapsed:.2f}s: {query_e}")
                
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_threat_model_queries())