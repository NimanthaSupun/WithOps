"""Quick script to check user installations in database"""
import asyncio
from database.config import db_manager
from database.operations import installation_repo

async def check_installations():
    user_id = "google-oauth2|104809585699210919063"
    
    async with db_manager.get_session() as session:
        installations = await installation_repo.get_user_installations(session, user_id)
        
        print(f"\n{'='*60}")
        print(f"Installations for user: {user_id}")
        print(f"{'='*60}")
        
        if not installations:
            print("❌ No installations found in database")
        else:
            print(f"✅ Found {len(installations)} installations:")
            for inst in installations:
                print(f"\n  Organization: {inst.organization_name}")
                print(f"  Installation ID: {inst.installation_id}")
                print(f"  Created: {inst.created_at}")
                print(f"  Updated: {inst.updated_at}")

if __name__ == "__main__":
    asyncio.run(check_installations())
