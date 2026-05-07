"""
Populate organization_name column in repository_trees table
This fixes the empty organization_name values by copying from organizations.login
"""
import asyncio
import logging
from sqlalchemy import text
from database.config import DatabaseManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def populate_organization_names():
    """Populate organization_name from organizations table"""
    db_manager = DatabaseManager()
    
    async with db_manager.get_session() as session:
        # Update repository_trees to set organization_name from organizations.login
        query = text("""
            UPDATE repository_trees rt
            SET organization_name = o.login
            FROM organizations o
            WHERE rt.organization_id = o.id
            AND (rt.organization_name IS NULL OR rt.organization_name = '')
        """)
        
        result = await session.execute(query)
        await session.commit()
        
        updated_count = result.rowcount
        logger.info(f"✅ Updated {updated_count} repository tree records with organization names")
        
        # Verify the update
        verify_query = text("""
            SELECT rt.id, rt.organization_id, rt.organization_name, o.login, rt.user_id
            FROM repository_trees rt
            LEFT JOIN organizations o ON rt.organization_id = o.id
            WHERE rt.is_active = true
            LIMIT 10
        """)
        
        result = await session.execute(verify_query)
        rows = result.fetchall()
        
        logger.info("\n📊 Verification - Repository Trees:")
        for row in rows:
            logger.info(f"  Tree ID: {row[0]}")
            logger.info(f"    Org ID: {row[1]}")
            logger.info(f"    Org Name (column): {row[2]}")
            logger.info(f"    Org Login (from orgs table): {row[3]}")
            logger.info(f"    User ID: {row[4]}")
            logger.info("")


if __name__ == "__main__":
    asyncio.run(populate_organization_names())
