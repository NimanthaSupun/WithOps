"""
Example usage of Workflow Orchestration Service API
Demonstrates all major endpoints and features
"""

import httpx
import asyncio


BASE_URL = "http://localhost:8107"  # Or via Kong: http://localhost:8000
USER_ID = "user-123"


async def check_health():
    """Check service health"""
    print("🔍 Checking service health...")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/health")
        print(f"Status: {response.json()}")
        print()


async def scan_workflow_security():
    """Scan a workflow for security vulnerabilities"""
    print("🔒 Scanning workflow for security issues...")
    
    workflow_content = """
name: CI Pipeline
on: [push, pull_request]

permissions:
  contents: write
  packages: write

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup
        run: |
          echo "API_KEY=sk-1234567890" >> .env
      - uses: some-action/deploy@v1
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
"""
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/security/scan/workflow",
            json={
                "workflow_content": workflow_content,
                "workflow_name": "ci.yml"
            },
            headers={"X-User-Id": USER_ID}
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Scan completed!")
            print(f"  Risk Level: {result['risk_level']}")
            print(f"  Risk Score: {result['risk_score']}/100")
            print(f"  Total Issues: {result['total_issues']}")
            print(f"  - Critical: {result['critical']}")
            print(f"  - High: {result['high']}")
            print(f"  - Medium: {result['medium']}")
            print(f"  - Low: {result['low']}")
            print("\n  Recommendations:")
            for rec in result['recommendations'][:3]:
                print(f"    • {rec}")
        else:
            print(f"❌ Scan failed: {response.status_code}")
    print()


async def save_project_tree():
    """Save project tree structure"""
    print("📁 Saving project tree...")
    
    tree_data = {
        "type": "folder",
        "name": "my-org",
        "children": [
            {
                "type": "folder",
                "name": ".github",
                "children": [
                    {
                        "type": "folder",
                        "name": "workflows",
                        "children": [
                            {
                                "type": "workflow",
                                "name": "ci.yml",
                                "path": ".github/workflows/ci.yml"
                            },
                            {
                                "type": "workflow",
                                "name": "deploy.yml",
                                "path": ".github/workflows/deploy.yml"
                            }
                        ]
                    }
                ]
            }
        ]
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/project-tree/my-org",
            json={
                "org_name": "my-org",
                "tree_data": tree_data
            },
            headers={"X-User-Id": USER_ID}
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Tree saved!")
            print(f"  Organization: {result['org_name']}")
            print(f"  Total Nodes: {result['node_count']}")
            print(f"  Workflows: {result['workflow_count']}")
            print(f"  Version: {result['version']}")
        else:
            print(f"❌ Save failed: {response.status_code}")
    print()


async def get_project_tree():
    """Retrieve saved project tree"""
    print("📂 Getting project tree...")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/project-tree/my-org",
            headers={"X-User-Id": USER_ID}
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Tree retrieved!")
            print(f"  Workflows found: {result['workflow_count']}")
        elif response.status_code == 404:
            print("ℹ️  No tree found for this organization")
        else:
            print(f"❌ Failed: {response.status_code}")
    print()


async def save_canvas_design():
    """Save workflow canvas design"""
    print("🎨 Saving canvas design...")
    
    design_data = {
        "nodes": [
            {
                "id": "checkout-1",
                "type": "action",
                "action": "actions/checkout@v4",
                "position": {"x": 100, "y": 100}
            },
            {
                "id": "setup-node-1",
                "type": "action",
                "action": "actions/setup-node@v4",
                "position": {"x": 100, "y": 200}
            },
            {
                "id": "test-1",
                "type": "command",
                "command": "npm test",
                "position": {"x": 100, "y": 300}
            }
        ],
        "edges": [
            {"from": "checkout-1", "to": "setup-node-1"},
            {"from": "setup-node-1", "to": "test-1"}
        ]
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/canvas/save-workflow",
            json={
                "org_name": "my-org",
                "repo_name": "my-repo",
                "design_data": design_data,
                "relationships": [
                    {
                        "source": "ci.yml",
                        "target": "deploy.yml",
                        "type": "triggers"
                    }
                ],
                "canvas_metadata": {
                    "created_with": "example_script",
                    "version": "1.0"
                }
            },
            headers={"X-User-Id": USER_ID}
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Canvas saved!")
            print(f"  Canvas ID: {result['canvas_id']}")
            print(f"  Nodes: {len(design_data['nodes'])}")
            print(f"  Version: {result['version']}")
        else:
            print(f"❌ Save failed: {response.status_code}")
    print()


async def get_predefined_actions():
    """Get library of predefined GitHub Actions"""
    print("📚 Getting predefined actions library...")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/canvas/predefined-actions?category=ci",
            headers={"X-User-Id": USER_ID}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Found {len(result.get('actions', []))} actions in CI category:")
            for action in result.get('actions', [])[:3]:
                print(f"  • {action['name']}: {action['action']}")
                print(f"    {action['description']}")
        else:
            print(f"❌ Failed: {response.status_code}")
    print()


async def get_security_overview():
    """Get security overview for organization"""
    print("📊 Getting security overview...")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/security/overview/my-org",
            headers={"X-User-Id": USER_ID}
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Security Overview:")
            print(f"  Total Scans: {result.get('total_scans', 0)}")
            print(f"  Total Issues: {result.get('total_issues', 0)}")
            
            risk_dist = result.get('risk_distribution', {})
            if risk_dist:
                print("  Risk Distribution:")
                for level, count in risk_dist.items():
                    if count > 0:
                        print(f"    - {level}: {count}")
        else:
            print("ℹ️  No security data available yet")
    print()


async def main():
    """Run all examples"""
    print("=" * 70)
    print("Workflow Orchestration Service - API Examples")
    print("=" * 70)
    print()
    
    try:
        # Basic checks
        await check_health()
        
        # Security scanning
        await scan_workflow_security()
        
        # Project tree management
        await save_project_tree()
        await get_project_tree()
        
        # Canvas design
        await save_canvas_design()
        await get_predefined_actions()
        
        # Security overview
        await get_security_overview()
        
        print("=" * 70)
        print("✅ All examples completed successfully!")
        print("=" * 70)
        print()
        print("📖 API Documentation: http://localhost:8107/docs")
        print("📊 Metrics: http://localhost:8107/metrics")
        print("💚 Health: http://localhost:8107/health")
        
    except httpx.ConnectError:
        print("❌ Could not connect to service!")
        print("Make sure the service is running:")
        print("  docker-compose up -d workflow-orchestration-service")
        print("Or:")
        print("  python main.py")
    except Exception as e:
        print(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())
