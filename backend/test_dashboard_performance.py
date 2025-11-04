#!/usr/bin/env python3
"""
Test database connectivity and performance for dashboard queries
"""
import asyncio
import time
import sys
import os

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.config import db_manager
from database.models import User, Organization, OrganizationInstallation, Repository, Workflow
from sqlalchemy import select, func

async def test_db_performance():
    """Test database operations performance"""
    print("🔍 Testing database connectivity and performance...")
    
    try:
        # Test basic connection
        start_time = time.time()
        async with db_manager.get_session() as session:
            # Simple query test
            result = await session.execute(select(func.count(User.id)))
            user_count = result.scalar()
            print(f"✅ Basic connection test passed. Users in database: {user_count}")
            print(f"   Connection time: {time.time() - start_time:.2f} seconds")
        
        # Test individual table queries
        tables_to_test = [
            (User, "users"),
            (Organization, "organizations"), 
            (OrganizationInstallation, "organization_installations"),
            (Repository, "repositories"),
            (Workflow, "workflows")
        ]
        
        for model, table_name in tables_to_test:
            start_time = time.time()
            try:
                async with db_manager.get_session() as session:
                    result = await session.execute(select(func.count(model.id)))
                    count = result.scalar()
                    elapsed = time.time() - start_time
                    print(f"✅ {table_name}: {count} records ({elapsed:.2f}s)")
            except Exception as e:
                print(f"❌ {table_name}: Error - {e}")
        
        # Test the complex JOIN query from dashboard
        print("\n🔍 Testing complex dashboard queries...")
        start_time = time.time()
        
        async with db_manager.get_session() as session:
            # Test a sample user query (if any users exist)
            user_query = select(User).limit(1)
            result = await session.execute(user_query)
            sample_user = result.scalar_one_or_none()
            
            if sample_user:
                print(f"   Testing with sample user: {sample_user.id}")
                
                # Test organizations query
                org_start = time.time()
                org_query = select(Organization).join(
                    OrganizationInstallation, Organization.id == OrganizationInstallation.organization_id
                ).where(OrganizationInstallation.user_id == sample_user.id)
                org_result = await session.execute(org_query)
                organizations = org_result.scalars().all()
                print(f"   Organizations query: {len(organizations)} results ({time.time() - org_start:.2f}s)")
                
                # Test repository count query
                repo_start = time.time()
                repo_count_query = select(func.count(Repository.id)).join(
                    OrganizationInstallation, Repository.installation_id == OrganizationInstallation.id
                ).where(OrganizationInstallation.user_id == sample_user.id)
                repo_count_result = await session.execute(repo_count_query)
                repo_count = repo_count_result.scalar() or 0
                print(f"   Repository count query: {repo_count} results ({time.time() - repo_start:.2f}s)")
                
                # Test workflow count query
                workflow_start = time.time()
                workflow_count_query = select(func.count(Workflow.id)).join(
                    Repository, Workflow.repository_id == Repository.id
                ).join(
                    OrganizationInstallation, Repository.installation_id == OrganizationInstallation.id
                ).where(OrganizationInstallation.user_id == sample_user.id)
                workflow_count_result = await session.execute(workflow_count_query)
                workflow_count = workflow_count_result.scalar() or 0
                print(f"   Workflow count query: {workflow_count} results ({time.time() - workflow_start:.2f}s)")
            else:
                print("   No users found to test complex queries")
        
        total_time = time.time() - start_time
        print(f"\n✅ Total dashboard query time: {total_time:.2f} seconds")
        
        if total_time > 25:
            print("⚠️  Dashboard queries are taking longer than expected!")
            print("   This could cause timeouts in the API")
        else:
            print("✅ Dashboard queries are performing well")
            
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_db_performance())