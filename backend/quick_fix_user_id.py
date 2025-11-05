"""
Quick fix: Reassign all threat models to the currently authenticated user.
Run this once to fix the orphaned threat models.
"""
import asyncio
from sqlalchemy import select
from database.config import DatabaseManager
from database.models import ThreatModel, User

async def fix_threat_models():
    """Reassign all threat models to the most recent user (current user)."""
    
    db_manager = DatabaseManager()
    async with db_manager.get_session() as session:
        # Get all users ordered by last_login (most recent first)
        users_result = await session.execute(
            select(User).order_by(User.last_login.desc())
        )
        users = users_result.scalars().all()
        
        if not users:
            print("❌ No users found!")
            return
        
        # Use the most recently logged in user (that's you!)
        current_user = users[0]
        print(f"\n✅ Current user: {current_user.email}")
        print(f"   User ID: {current_user.id}")
        print(f"   Auth ID: {current_user.auth_user_id}")
        
        # Get all threat models
        models_result = await session.execute(select(ThreatModel))
        all_models = models_result.scalars().all()
        
        print(f"\n📊 Found {len(all_models)} threat models in database")
        
        # Reassign all models to current user
        migrated = 0
        for model in all_models:
            if model.user_id != current_user.id:
                old_id = model.user_id
                model.user_id = current_user.id
                print(f"   ✓ '{model.name}': {old_id} → {current_user.id}")
                migrated += 1
        
        await session.commit()
        
        print(f"\n✅ Success! Migrated {migrated} models to {current_user.email}")
        print(f"   Total models now: {len(all_models)}")
        print("\n🔄 Refresh your browser to see all threat models!")

if __name__ == "__main__":
    asyncio.run(fix_threat_models())
