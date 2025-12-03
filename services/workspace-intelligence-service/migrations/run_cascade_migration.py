"""
Migration script to add CASCADE delete to all foreign keys referencing project_analyses
This allows automatic deletion of related records when an analysis is deleted
"""

import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database connection string from environment
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://postgres.fcmcsbmsntmpeyjltqbi:5m19NTF6y0x1fJgr@aws-0-ap-south-1.pooler.supabase.com:5432/postgres'
)

def run_migration():
    """Run the CASCADE delete migration for all related tables"""
    conn = None
    try:
        print("🔌 Connecting to database...")
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Migration 1: repository_findings table
        print("\n📋 Updating repository_findings foreign key constraint...")
        cursor.execute("""
            ALTER TABLE repository_findings 
            DROP CONSTRAINT IF EXISTS repository_findings_analysis_id_fkey;
        """)
        
        cursor.execute("""
            ALTER TABLE repository_findings 
            ADD CONSTRAINT repository_findings_analysis_id_fkey 
            FOREIGN KEY (analysis_id) 
            REFERENCES project_analyses(id) 
            ON DELETE CASCADE;
        """)
        print("✅ repository_findings constraint updated")
        
        # Migration 2: maturity_scores table
        print("\n📋 Updating maturity_scores foreign key constraint...")
        cursor.execute("""
            ALTER TABLE maturity_scores 
            DROP CONSTRAINT IF EXISTS maturity_scores_analysis_id_fkey;
        """)
        
        cursor.execute("""
            ALTER TABLE maturity_scores 
            ADD CONSTRAINT maturity_scores_analysis_id_fkey 
            FOREIGN KEY (analysis_id) 
            REFERENCES project_analyses(id) 
            ON DELETE CASCADE;
        """)
        print("✅ maturity_scores constraint updated")
        
        # Verify all constraints
        print("\n✅ Verifying all constraints...")
        cursor.execute("""
            SELECT 
                tc.constraint_name, 
                tc.table_name, 
                kcu.column_name,
                rc.delete_rule
            FROM information_schema.table_constraints AS tc 
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.referential_constraints AS rc
                ON tc.constraint_name = rc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY' 
                AND kcu.column_name = 'analysis_id'
                AND rc.unique_constraint_name IN (
                    SELECT constraint_name 
                    FROM information_schema.table_constraints 
                    WHERE table_name = 'project_analyses' 
                    AND constraint_type = 'PRIMARY KEY'
                );
        """)
        
        results = cursor.fetchall()
        print(f"\n📊 Found {len(results)} foreign key constraints referencing project_analyses:")
        all_cascade = True
        for constraint_name, table_name, column_name, delete_rule in results:
            status = "✅" if delete_rule == "CASCADE" else "❌"
            print(f"   {status} {table_name}.{column_name} -> {delete_rule}")
            if delete_rule != "CASCADE":
                all_cascade = False
        
        if all_cascade:
            print("\n🎉 All constraints have CASCADE delete enabled!")
        else:
            print("\n⚠️ Warning: Some constraints do not have CASCADE delete")
        
        conn.commit()
        print("\n✅ Migration completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            cursor.close()
            conn.close()
            print("🔌 Database connection closed")

if __name__ == "__main__":
    run_migration()
