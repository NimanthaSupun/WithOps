"""
Show all users and let you pick the correct one to migrate threat models to.
"""
import asyncio
from sqlalchemy import select
from database.config import DatabaseManager
from database.models import ThreatModel, User

async def show_users_and_migrate():
    """Show all users and let user pick which one to migrate to."""
    
    db_manager = DatabaseManager()
    async with db_manager.get_session() as session:
        # Get all users
        users_result = await session.execute(
            select(User).order_by(User.last_login.desc())
        )
        users = users_result.scalars().all()
        
        if not users:
            print("❌ No users found!")
            return
        
        print("\n" + "="*70)
        print("ALL USERS IN DATABASE")
        print("="*70)
        for i, user in enumerate(users, 1):
            print(f"\n{i}. Email: {user.email}")
            print(f"   User ID: {user.id}")
            print(f"   Auth ID: {user.auth_user_id}")
            print(f"   GitHub: {user.github_username or 'N/A'}")
            print(f"   Last Login: {user.last_login}")
        
        # Get all threat models
        models_result = await session.execute(select(ThreatModel))
        all_models = models_result.scalars().all()
        
        print(f"\n" + "="*70)
        print(f"📊 Total threat models in database: {len(all_models)}")
        print("="*70)
        
        # Show which user owns each model
        for i, model in enumerate(all_models, 1):
            owner = next((u for u in users if u.id == model.user_id), None)
            owner_email = owner.email if owner else "UNKNOWN"
            print(f"{i}. '{model.name}' - Owner: {owner_email} (ID: {model.user_id})")
        
        # Ask user to select
        print("\n" + "="*70)
        print("SELECT YOUR ACCOUNT")
        print("="*70)
        
        while True:
            try:
                choice = input(f"\nWhich user are YOU? Enter number (1-{len(users)}): ").strip()
                choice_num = int(choice)
                if 1 <= choice_num <= len(users):
                    target_user = users[choice_num - 1]
                    break
                print(f"❌ Please enter a number between 1 and {len(users)}")
            except (ValueError, KeyboardInterrupt):
                print("\n❌ Migration cancelled")
                return
        
        print(f"\n✅ Selected user: {target_user.email}")
        print(f"   User ID: {target_user.id}")
        print(f"   Auth ID: {target_user.auth_user_id}")
        
        # Count models that need migration
        models_to_migrate = [m for m in all_models if m.user_id != target_user.id]
        
        if not models_to_migrate:
            print(f"\n✅ All {len(all_models)} models already belong to {target_user.email}")
            print("No migration needed!")
            return
        
        # Confirm migration
        print(f"\n" + "="*70)
        print("MIGRATION PLAN")
        print("="*70)
        print(f"Will reassign {len(models_to_migrate)} models to: {target_user.email}")
        print("\nModels to migrate:")
        for model in models_to_migrate:
            print(f"  • '{model.name}'")
        
        confirm = input("\nProceed with migration? (yes/no): ").strip().lower()
        
        if confirm != 'yes':
            print("❌ Migration cancelled")
            return
        
        # Perform migration
        print(f"\n🔄 Migrating...")
        for model in models_to_migrate:
            old_id = model.user_id
            model.user_id = target_user.id
            print(f"   ✓ '{model.name}': {old_id[:8]}... → {target_user.id[:8]}...")
        
        await session.commit()
        
        print(f"\n✅ Success! Migrated {len(models_to_migrate)} models to {target_user.email}")
        print(f"   Total models for {target_user.email}: {len(all_models)}")
        print("\n🔄 Refresh your browser to see all threat models!")

if __name__ == "__main__":
    asyncio.run(show_users_and_migrate())
