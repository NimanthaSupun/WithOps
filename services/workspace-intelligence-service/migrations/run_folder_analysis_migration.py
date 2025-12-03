"""
Migration: Add folder-level analysis support
Adds columns to project_analyses table for tracking analysis scope
"""

import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database connection string
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://postgres.fcmcsbmsntmpeyjltqbi:5m19NTF6y0x1fJgr@aws-0-ap-south-1.pooler.supabase.com:5432/postgres'
)

def run_migration():
    """Add folder-level analysis support columns"""
    conn = None
    try:
        print("🔌 Connecting to database...")
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        print("\n📋 Adding analysis_scope column...")
        cursor.execute("""
            ALTER TABLE project_analyses 
            ADD COLUMN IF NOT EXISTS analysis_scope VARCHAR(50) DEFAULT 'organization';
        """)
        
        print("📋 Adding folder_id column...")
        cursor.execute("""
            ALTER TABLE project_analyses 
            ADD COLUMN IF NOT EXISTS folder_id VARCHAR(255);
        """)
        
        print("📋 Creating index on folder_id...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_project_analyses_folder_id 
            ON project_analyses(folder_id);
        """)
        
        print("📋 Adding folder_path column...")
        cursor.execute("""
            ALTER TABLE project_analyses 
            ADD COLUMN IF NOT EXISTS folder_path VARCHAR(500);
        """)
        
        print("📋 Adding repositories_in_scope column...")
        cursor.execute("""
            ALTER TABLE project_analyses 
            ADD COLUMN IF NOT EXISTS repositories_in_scope JSONB;
        """)
        
        print("\n🔄 Updating existing records...")
        cursor.execute("""
            UPDATE project_analyses 
            SET analysis_scope = 'organization' 
            WHERE analysis_scope IS NULL;
        """)
        updated_rows = cursor.rowcount
        print(f"   Updated {updated_rows} existing records to 'organization' scope")
        
        print("\n✅ Verifying migration...")
        cursor.execute("""
            SELECT 
                column_name, 
                data_type, 
                is_nullable,
                column_default
            FROM information_schema.columns 
            WHERE table_name = 'project_analyses' 
                AND column_name IN ('analysis_scope', 'folder_id', 'folder_path', 'repositories_in_scope')
            ORDER BY ordinal_position;
        """)
        
        columns = cursor.fetchall()
        print(f"\n📊 Verified {len(columns)} new columns:")
        for col_name, data_type, nullable, default in columns:
            nullable_str = "NULL" if nullable == "YES" else "NOT NULL"
            default_str = f"DEFAULT {default}" if default else ""
            print(f"   ✓ {col_name:<25} {data_type:<20} {nullable_str:<10} {default_str}")
        
        conn.commit()
        print("\n🎉 Migration completed successfully!")
        print("✅ Folder-level analysis support is now enabled")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            cursor.close()
            conn.close()
            print("\n🔌 Database connection closed")

if __name__ == "__main__":
    run_migration()
