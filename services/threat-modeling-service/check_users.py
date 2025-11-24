"""Check users table mapping"""
import asyncio
from sqlalchemy import text
from database import db_manager

async def check_users():
    """Check user mapping"""
    try:
        async with db_manager.get_session() as session:
            # Check users table
            result = await session.execute(
                text("SELECT id, auth_user_id, email FROM users WHERE auth_user_id = 'google-oauth2|104809585699210919063'")
            )
            user = result.fetchone()
            
            if user:
                print(f"\n✅ Found user mapping:")
                print(f"  Internal UUID: {user[0]}")
                print(f"  Auth0 ID: {user[1]}")
                print(f"  Email: {user[2]}")
                print(f"\n🔍 This UUID should match threat_models.user_id")
            else:
                print(f"\n❌ No user found with auth_user_id: google-oauth2|104809585699210919063")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_users())
