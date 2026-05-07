"""
Migration: Add AI Analysis History Table
Creates a new table to store all AI analysis results instead of just the latest one
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from database.config import db_manager
from database.models import AIAnalysisHistory
from sqlalchemy import inspect

def run_migration():
    """Create the ai_analysis_history table if it doesn't exist"""
    inspector = inspect(db_manager.sync_engine)
    existing_tables = inspector.get_table_names()
    
    if 'ai_analysis_history' in existing_tables:
        print("✅ Table 'ai_analysis_history' already exists")
        return
    
    print("🔧 Creating 'ai_analysis_history' table...")
    
    # Create only the new table
    AIAnalysisHistory.__table__.create(db_manager.sync_engine)
    
    print("✅ Migration completed successfully!")
    print("📊 Table 'ai_analysis_history' created")

if __name__ == "__main__":
    run_migration()
