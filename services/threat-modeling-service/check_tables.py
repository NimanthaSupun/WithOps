import sqlite3

conn = sqlite3.connect('threat_modeling.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]
print("\n✅ Database Tables:")
for table in tables:
    print(f"  - {table}")
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    count = cursor.fetchone()[0]
    print(f"    Records: {count}")
conn.close()
