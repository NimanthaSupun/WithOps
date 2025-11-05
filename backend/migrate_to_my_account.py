"""
Migrate all threat models to NimanthaSupun user
"""
import asyncio
from sqlalchemy import select
from database.config import DatabaseManager
from database.models import ThreatModel, User

async def migrate_to_nimantha():
    """Migrate all threat models to NimanthaSupun."""
    
    db_manager = DatabaseManager()
    async with db_manager.get_session() as session:
        # Find NimanthaSupun user
        result = await session.execute(
            select(User).where(User.github_username == 'NimanthaSupun')
        )
        nimantha_user = result.scalars().first()
        
        if not nimantha_user:
            print("❌ NimanthaSupun user not found!")
            return
        
        print(f"\n✅ Found user: {nimantha_user.github_username}")
        print(f"   Email: {nimantha_user.email}")
        print(f"   User ID: {nimantha_user.id}")
        print(f"   Auth ID: {nimantha_user.auth_user_id}")
        
        # Get all threat models
        models_result = await session.execute(select(ThreatModel))
        all_models = models_result.scalars().all()
        
        print(f"\n📊 Found {len(all_models)} threat models")
        
        # Migrate all to Nimantha
        migrated = 0
        for model in all_models:
            if model.user_id != nimantha_user.id:
                old_id = model.user_id
                model.user_id = nimantha_user.id
                print(f"   ✓ Migrated '{model.name}'")
                migrated += 1
        
        await session.commit()
        
        print(f"\n✅ Success!")
        print(f"   Migrated: {migrated} models")
        print(f"   Total models for NimanthaSupun: {len(all_models)}")
        print("\n🔄 Refresh your browser to see all {len(all_models)} threat models!")

if __name__ == "__main__":
    asyncio.run(migrate_to_nimantha())
