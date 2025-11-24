"""Check what user_ids exist in threat_models table"""
import asyncio
from sqlalchemy import select, text
from database import db_manager, ThreatModel

async def check_user_ids():
    """Check user_ids in threat_models table"""
    try:
        async with db_manager.get_session() as session:
            # Get all distinct user_ids
            result = await session.execute(
                text("SELECT DISTINCT user_id FROM threat_models LIMIT 10")
            )
            user_ids = [row[0] for row in result.fetchall()]
            
            print(f"\n{'='*80}")
            print(f"Found {len(user_ids)} distinct user_ids in threat_models table:")
            print(f"{'='*80}")
            for uid in user_ids:
                print(f"  - {uid}")
            
            # Count total models
            count_result = await session.execute(
                text("SELECT COUNT(*) FROM threat_models")
            )
            total = count_result.scalar()
            print(f"\n📊 Total threat models in database: {total}")
            
            # Get a sample model to see structure
            sample_result = await session.execute(
                text("SELECT id, name, user_id, organization_id FROM threat_models LIMIT 1")
            )
            sample = sample_result.fetchone()
            if sample:
                print(f"\n🔍 Sample model:")
                print(f"  ID: {sample[0]}")
                print(f"  Name: {sample[1]}")
                print(f"  User ID: {sample[2]}")
                print(f"  Org ID: {sample[3]}")
                
            print(f"\n{'='*80}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_user_ids())
