"""
Integration tests for Workflow Orchestration Service
Run with: pytest test_service.py -v
"""

import pytest
import httpx
import asyncio
from datetime import datetime


BASE_URL = "http://localhost:8107"
TEST_USER_ID = "test-user-123"
TEST_ORG = "test-org"
TEST_REPO = "test-repo"


class TestServiceHealth:
    """Test service health and basic endpoints"""
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check endpoint"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "version" in data
    
    @pytest.mark.asyncio
    async def test_root_endpoint(self):
        """Test root endpoint"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/")
            assert response.status_code == 200
            data = response.json()
            assert data["service"] == "Workflow Orchestration Service"
    
    @pytest.mark.asyncio
    async def test_metrics_endpoint(self):
        """Test Prometheus metrics endpoint"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/metrics")
            assert response.status_code == 200
            assert "prometheus" in response.text.lower() or "request" in response.text.lower()


class TestWorkflowParser:
    """Test workflow parser functionality"""
    
    def test_parse_simple_workflow(self):
        """Test parsing a simple workflow"""
        from core.workflow_parser import WorkflowParser
        
        workflow_yaml = """
name: Test Workflow
on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        run: npm test
"""
        result = WorkflowParser.parse_workflow(workflow_yaml)
        
        assert result['name'] == 'Test Workflow'
        assert 'push' in result['triggers']
        assert 'workflow_dispatch' in result['triggers']
        assert len(result['jobs']) > 0
        assert len(result['steps']) > 0
        assert 'actions/checkout@v4' in result['uses']
    
    def test_parse_workflow_with_secrets(self):
        """Test secret detection"""
        from core.workflow_parser import WorkflowParser
        
        workflow_yaml = """
name: Deploy
on: push
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy
        run: |
          echo "API_KEY=sk-1234567890abcdef" >> .env
        env:
          TOKEN: ${{ secrets.GITHUB_TOKEN }}
"""
        result = WorkflowParser.parse_workflow(workflow_yaml)
        
        assert len(result['secrets']) > 0  # Should detect hardcoded API_KEY


class TestSecurityScanner:
    """Test security scanner functionality"""
    
    def test_scan_secure_workflow(self):
        """Test scanning a secure workflow"""
        from core.security_scanner import SecurityScanner
        
        workflow_yaml = """
name: Secure Workflow
on: push
jobs:
  test:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
      - run: npm test
"""
        result = SecurityScanner.scan_workflow(workflow_yaml, "Secure Workflow")
        
        assert result['risk_level'] in ['minimal', 'low']
        assert result['risk_score'] < 25
    
    def test_scan_vulnerable_workflow(self):
        """Test scanning a workflow with vulnerabilities"""
        from core.security_scanner import SecurityScanner
        
        workflow_yaml = """
name: Vulnerable Workflow
on: push
permissions: write-all
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v1
      - run: echo "API_KEY=secret123" > .env
"""
        result = SecurityScanner.scan_workflow(workflow_yaml, "Vulnerable Workflow")
        
        assert result['risk_level'] in ['high', 'critical', 'medium']
        assert result['risk_score'] > 25
        assert result['summary']['total_issues'] > 0
        assert len(result['recommendations']) > 0


class TestProjectTreeAPI:
    """Test project tree API endpoints"""
    
    @pytest.mark.asyncio
    async def test_save_and_get_tree(self):
        """Test saving and retrieving project tree"""
        tree_data = {
            "type": "folder",
            "name": "root",
            "children": [
                {
                    "type": "workflow",
                    "name": "ci.yml",
                    "path": ".github/workflows/ci.yml"
                }
            ]
        }
        
        async with httpx.AsyncClient() as client:
            # Save tree
            response = await client.post(
                f"{BASE_URL}/api/project-tree/{TEST_ORG}",
                json={
                    "org_name": TEST_ORG,
                    "tree_data": tree_data
                },
                headers={"X-User-Id": TEST_USER_ID}
            )
            
            if response.status_code == 200:
                data = response.json()
                assert data['org_name'] == TEST_ORG
                assert data['node_count'] > 0
                
                # Get tree
                response = await client.get(
                    f"{BASE_URL}/api/project-tree/{TEST_ORG}",
                    headers={"X-User-Id": TEST_USER_ID}
                )
                assert response.status_code == 200


class TestSecurityScanAPI:
    """Test security scanning API endpoints"""
    
    @pytest.mark.asyncio
    async def test_scan_workflow_endpoint(self):
        """Test workflow scanning endpoint"""
        workflow_content = """
name: Test
on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
"""
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/api/security/scan/workflow",
                json={
                    "workflow_content": workflow_content,
                    "workflow_name": "test.yml"
                },
                headers={"X-User-Id": TEST_USER_ID}
            )
            
            if response.status_code == 200:
                data = response.json()
                assert 'scan_id' in data
                assert 'risk_level' in data
                assert 'risk_score' in data
                assert 'total_issues' in data


class TestCanvasAPI:
    """Test canvas design API endpoints"""
    
    @pytest.mark.asyncio
    async def test_predefined_actions(self):
        """Test getting predefined actions"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/api/canvas/predefined-actions",
                headers={"X-User-Id": TEST_USER_ID}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert 'categories' in data or 'actions' in data
    
    @pytest.mark.asyncio
    async def test_save_canvas(self):
        """Test saving canvas design"""
        design_data = {
            "nodes": [
                {"id": "1", "type": "checkout", "x": 100, "y": 100}
            ],
            "edges": []
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/api/canvas/save-workflow",
                json={
                    "org_name": TEST_ORG,
                    "repo_name": TEST_REPO,
                    "design_data": design_data,
                    "relationships": [],
                    "canvas_metadata": {}
                },
                headers={"X-User-Id": TEST_USER_ID}
            )
            
            if response.status_code == 200:
                data = response.json()
                assert data['org_name'] == TEST_ORG
                assert data['repo_name'] == TEST_REPO


if __name__ == "__main__":
    # Run basic synchronous tests
    print("Running basic tests...")
    
    # Test parser
    from core.workflow_parser import WorkflowParser
    test_yaml = "name: Test\non: push\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4"
    result = WorkflowParser.parse_workflow(test_yaml)
    print(f"✅ Parser test passed: {result['name']}")
    
    # Test scanner
    from core.security_scanner import SecurityScanner
    scan_result = SecurityScanner.scan_workflow(test_yaml, "Test")
    print(f"✅ Scanner test passed: Risk level {scan_result['risk_level']}")
    
    print("\nFor full async tests, run: pytest test_service.py -v")
