"""
Migration script to reassign threat models from old test user to current authenticated user.
This fixes the issue where threat models were created with a different user_id.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, update
from database.config import DatabaseManager
from database.models import ThreatModel, User
import logging

logger = logging.getLogger(__name__)


async def migrate_threat_models():
    """Reassign all threat models to the current authenticated user."""
    
    db_manager = DatabaseManager()
    async with db_manager.get_session() as session:
        try:
            # Get all users
            users_result = await session.execute(select(User))
            users = users_result.scalars().all()
            
            if not users:
                logger.error("❌ No users found in database!")
                return
            
            logger.info(f"👥 Found {len(users)} users:")
            for i, user in enumerate(users, 1):
                logger.info(f"  {i}. ID: {user.id} | Email: {user.email} | Auth ID: {user.auth_user_id}")
            
            # Get all threat models
            models_result = await session.execute(select(ThreatModel))
            all_models = models_result.scalars().all()
            
            logger.info(f"\n📊 Found {len(all_models)} threat models:")
            for i, model in enumerate(all_models, 1):
                logger.info(f"  {i}. '{model.name}' - Current user_id: {model.user_id}")
            
            if len(users) == 1:
                # Only one user - automatically migrate to them
                target_user = users[0]
                logger.info(f"\n✅ Only one user found. Will migrate all models to: {target_user.email}")
            else:
                # Multiple users - ask which one
                print("\n" + "="*70)
                print("MIGRATION TARGET SELECTION")
                print("="*70)
                print("\nWhich user should own these threat models?")
                for i, user in enumerate(users, 1):
                    print(f"  {i}. {user.email} (ID: {user.id})")
                
                while True:
                    try:
                        choice = int(input("\nEnter user number (1-{}): ".format(len(users))))
                        if 1 <= choice <= len(users):
                            target_user = users[choice - 1]
                            break
                        print(f"❌ Please enter a number between 1 and {len(users)}")
                    except ValueError:
                        print("❌ Please enter a valid number")
            
            # Count models that need migration
            models_to_migrate = [m for m in all_models if m.user_id != target_user.id]
            
            if not models_to_migrate:
                logger.info(f"\n✅ All {len(all_models)} models already belong to {target_user.email}")
                logger.info("No migration needed!")
                return
            
            logger.info(f"\n📋 Migration Plan:")
            logger.info(f"  • Target User: {target_user.email} (ID: {target_user.id})")
            logger.info(f"  • Models to migrate: {len(models_to_migrate)}")
            logger.info(f"  • Models already correct: {len(all_models) - len(models_to_migrate)}")
            
            # Confirm migration
            print("\n" + "="*70)
            print("CONFIRM MIGRATION")
            print("="*70)
            print(f"\nThis will reassign {len(models_to_migrate)} threat models to:")
            print(f"  {target_user.email} (ID: {target_user.id})")
            print("\nModels to be migrated:")
            for model in models_to_migrate:
                print(f"  • '{model.name}' (ID: {model.id})")
            
            confirm = input("\nProceed with migration? (yes/no): ").lower().strip()
            
            if confirm != 'yes':
                logger.info("❌ Migration cancelled by user")
                return
            
            # Perform migration
            logger.info(f"\n🔄 Starting migration...")
            
            for model in models_to_migrate:
                old_user_id = model.user_id
                model.user_id = target_user.id
                logger.info(f"  ✓ Migrated '{model.name}': {old_user_id} → {target_user.id}")
            
            await session.commit()
            
            logger.info(f"\n✅ Migration completed successfully!")
            logger.info(f"  • {len(models_to_migrate)} models migrated to {target_user.email}")
            logger.info(f"  • Total models for {target_user.email}: {len(all_models)}")
            
            # Verify migration
            logger.info(f"\n🔍 Verifying migration...")
            verify_result = await session.execute(
                select(ThreatModel).where(ThreatModel.user_id == target_user.id)
            )
            migrated_models = verify_result.scalars().all()
            
            logger.info(f"✅ Verification: {len(migrated_models)} models now belong to {target_user.email}")
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            raise


async def main():
    """Main entry point."""
    logger.info("="*70)
    logger.info("THREAT MODEL USER MIGRATION TOOL")
    logger.info("="*70)
    logger.info("\nThis tool will reassign threat models from old test users to your current user.\n")
    
    try:
        await migrate_threat_models()
        logger.info("\n" + "="*70)
        logger.info("Migration completed! You can now refresh your threat modeling page.")
        logger.info("="*70)
    except Exception as e:
        logger.error(f"\n❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
