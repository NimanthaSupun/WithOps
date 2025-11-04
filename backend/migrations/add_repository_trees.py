"""
Migration: Add repository_trees table
Purpose: Separate repository folder structure for workspace analysis and DevSecOps intelligence
Date: 2025-10-12
"""

import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from database.config import SupabaseConfig
from database.models import Base, RepositoryTree
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration():
    """Create repository_trees table"""
    
    try:
        # Get database URL
        config = SupabaseConfig()
        database_url = config.database_url
        logger.info(f"Connecting to database...")
        
        # Create engine
        engine = create_engine(database_url)
        
        # Create only the RepositoryTree table
        logger.info("Creating repository_trees table...")
        RepositoryTree.__table__.create(engine, checkfirst=True)
        logger.info("✅ repository_trees table created successfully")
        
        # Verify table exists
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name = 'repository_trees'
            """))
            
            if result.fetchone():
                logger.info("✅ Verified: repository_trees table exists in database")
            else:
                logger.error("❌ Error: repository_trees table not found after creation")
                return False
        
        logger.info("\n🎉 Migration completed successfully!")
        logger.info("\n📊 Repository Tree Table Structure:")
        logger.info("  - id: Primary key")
        logger.info("  - organization_id: FK to organizations")
        logger.info("  - user_id: FK to users")
        logger.info("  - tree_data: JSON (folder and repository structure)")
        logger.info("  - name: Tree name")
        logger.info("  - description: Optional description")
        logger.info("  - version: Version number (auto-increments)")
        logger.info("  - is_active: Soft delete flag")
        logger.info("  - analysis_status: Future workspace analysis status")
        logger.info("  - last_analyzed_at: Timestamp of last analysis")
        logger.info("  - maturity_score: DevSecOps maturity score (0-100)")
        logger.info("  - analysis_metadata: JSON (future AI findings)")
        logger.info("  - created_at: Timestamp")
        logger.info("  - updated_at: Timestamp")
        
        logger.info("\n📝 This table is SEPARATE from project_trees (workflow treeview)")
        logger.info("   Purpose: Workspace analysis & DevSecOps intelligence")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n" + "="*70)
    print("  MIGRATION: Add repository_trees table")
    print("  Separate from workflow treeview (project_trees)")
    print("="*70 + "\n")
    
    success = run_migration()
    
    if success:
        print("\n✅ Migration completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)
