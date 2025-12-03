"""
Simple migration script to add analysis_data column to project_analyses table
Connects directly to Supabase using psycopg2
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def run_migration():
    try:
        import psycopg2
        from psycopg2 import sql
    except ImportError:
        print("❌ psycopg2 not installed. Installing...")
        os.system(f"{sys.executable} -m pip install psycopg2-binary")
        import psycopg2
        from psycopg2 import sql
    
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        print("❌ DATABASE_URL not found in environment")
        return
    
    print(f"🔄 Connecting to database...")
    
    try:
        # Connect to the database
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        print("✅ Connected to database")
        print("🔄 Checking if analysis_data column exists...")
        
        # Check if column already exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'project_analyses' 
            AND column_name = 'analysis_data'
        """)
        
        existing = cursor.fetchone()
        
        if existing:
            print("✅ Column 'analysis_data' already exists, no migration needed")
        else:
            print("🔄 Adding analysis_data column to project_analyses table...")
            
            # Add the column
            cursor.execute("""
                ALTER TABLE project_analyses 
                ADD COLUMN analysis_data JSONB
            """)
            
            conn.commit()
            print("✅ Successfully added analysis_data column to project_analyses table")
        
        cursor.close()
        conn.close()
        
        print("✅ Migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        if 'conn' in locals():
            conn.rollback()
        raise


if __name__ == "__main__":
    run_migration()
