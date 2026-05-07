"""
Migration: Add Workspace Intelligence & DevSecOps Maturity Models
Adds tables for project analysis, findings, maturity scores, embeddings, and query history
"""

import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from database.config import SupabaseConfig
from database.models import (
    ProjectAnalysis, 
    RepositoryFinding, 
    MaturityScore, 
    WorkflowEmbedding, 
    QueryHistory
)
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration():
    """Create workspace intelligence tables"""
    try:
        # Get database URL
        config = SupabaseConfig()
        database_url = config.database_url
        logger.info("Connecting to database...")
        
        # Create engine
        engine = create_engine(database_url)
        
        # Create tables
        logger.info("Creating workspace intelligence tables...")
        
        # Only create the new tables
        ProjectAnalysis.__table__.create(engine, checkfirst=True)
        logger.info("✅ project_analyses table created")
        
        RepositoryFinding.__table__.create(engine, checkfirst=True)
        logger.info("✅ repository_findings table created")
        
        MaturityScore.__table__.create(engine, checkfirst=True)
        logger.info("✅ maturity_scores table created")
        
        WorkflowEmbedding.__table__.create(engine, checkfirst=True)
        logger.info("✅ workflow_embeddings table created")
        
        QueryHistory.__table__.create(engine, checkfirst=True)
        logger.info("✅ query_history table created")
        
        # Verify tables exist
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name IN ('project_analyses', 'repository_findings', 'maturity_scores', 'workflow_embeddings', 'query_history')
            """))
            
            tables = [row[0] for row in result.fetchall()]
            logger.info(f"✅ Verified {len(tables)} tables created: {', '.join(tables)}")
        
        logger.info("\n🎉 Migration completed successfully!")
        logger.info("\n📊 Workspace Intelligence Tables:")
        logger.info("  - project_analyses: Analysis results per project")
        logger.info("  - repository_findings: Security findings per repository")
        logger.info("  - maturity_scores: OWASP DSOMM maturity scores")
        logger.info("  - workflow_embeddings: AI embeddings for RAG")
        logger.info("  - query_history: User query history")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {str(e)}")
        raise


if __name__ == "__main__":
    run_migration()
