#!/usr/bin/env python3
"""
Supabase database connection diagnostics
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_supabase_config():
    """Check Supabase configuration"""
    print("🔍 Checking Supabase Configuration...")
    
    # Check environment variables
    supabase_url = os.getenv('SUPABASE_URL')
    database_url = os.getenv('SUPABASE_DATABASE_URL')
    local_db_url = os.getenv('LOCAL_DATABASE_URL')
    
    print(f"SUPABASE_URL: {supabase_url}")
    print(f"SUPABASE_DATABASE_URL: {'***masked***' if database_url else 'NOT SET'}")
    print(f"LOCAL_DATABASE_URL: {'***masked***' if local_db_url else 'NOT SET'}")
    
    if database_url:
        # Parse the database URL to check components
        if 'fcmcsbmsntmpeyjltqbi.supabase.co' in database_url:
            print("✅ Using Supabase cloud database")
        else:
            print("⚠️  Database URL doesn't point to expected Supabase instance")
    
    # Check which database will be used
    active_db = local_db_url or database_url or "sqlite+aiosqlite:///./devsecops.db"
    print(f"🎯 Active Database: {active_db}")
    
    if active_db.startswith('sqlite'):
        print("📁 Using SQLite database (local)")
    elif 'supabase.co' in active_db:
        print("☁️  Using Supabase cloud database")
        print("🌐 Testing network connectivity to Supabase...")
        
        # Try to resolve the hostname
        import socket
        try:
            hostname = 'db.fcmcsbmsntmpeyjltqbi.supabase.co'
            ip = socket.gethostbyname(hostname)
            print(f"✅ DNS resolution successful: {hostname} -> {ip}")
        except Exception as e:
            print(f"❌ DNS resolution failed: {e}")
            
        # Try to connect to the port
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)  # 10 second timeout
            result = sock.connect_ex((hostname, 5432))
            sock.close()
            
            if result == 0:
                print("✅ Network connection to Supabase successful")
            else:
                print(f"❌ Network connection failed: error code {result}")
        except Exception as e:
            print(f"❌ Network test failed: {e}")
    
    return active_db

if __name__ == "__main__":
    check_supabase_config()