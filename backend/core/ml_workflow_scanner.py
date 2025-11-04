"""
Core ML Workflow Security Scanner

Integrates the trained ML models with GitHub workflows to provide real-time security analysis.
This service bridges our ML pipeline with the existing GitHub client architecture.
"""

import os
import asyncio
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import logging
from pathlib import Path

try:
    # Import ML components from the ml_scanner package
    from ml_scanner.feature_extractor import WorkflowFeatureExtractor
    from ml_scanner.security_analyzer import WorkflowSecurityAnalyzer
    from ml_scanner.workflow_predictor import WorkflowSecurityPredictor
    
except ImportError as e:
    logging.warning(f"ML scanner modules not available: {e}. Scanner will run in fallback mode.")
    WorkflowFeatureExtractor = None
    WorkflowSecurityAnalyzer = None
    WorkflowSecurityPredictor = None
except Exception as e:
    logging.warning(f"Error loading ML components: {e}. Scanner will run in fallback mode.")
    WorkflowFeatureExtractor = None
    WorkflowSecurityAnalyzer = None  
    WorkflowSecurityPredictor = None

logger = logging.getLogger(__name__)

class MLWorkflowScanner:
    """
    Production ML workflow security scanner that integrates with existing DevSecOps platform.
    
    Features:
    - Real-time workflow security analysis
    - Risk scoring (0-100 scale)
    - Vulnerability pattern detection
    - Historical scan tracking
    - Organization-level security insights
    """
    
    def __init__(self):
        self.models_loaded = False
        self.feature_extractor = None
        self.model_trainer = None
        self.vulnerability_injector = None
        self.models = {}
        
        # Initialize components
        self._initialize_ml_components()
    
    def _initialize_ml_components(self):
        """Initialize ML components with fallback handling."""
        try:
            if WorkflowFeatureExtractor is None:
                logger.warning("ML components not available. Running in fallback mode.")
                return
            
            # Initialize feature extractor
            self.feature_extractor = WorkflowFeatureExtractor()
            logger.info("[SUCCESS] Feature extractor initialized")
            
            # Initialize security analyzer  
            self.security_analyzer = WorkflowSecurityAnalyzer()
            logger.info("[SUCCESS] Security analyzer initialized")
            
            # Initialize workflow predictor with correct model path
            models_dir = Path(__file__).parent.parent / "ml_scanner" / "data" / "ml_dataset"
            rf_model_path = models_dir / "random_forest_model.pkl"
            
            if rf_model_path.exists():
                self.workflow_predictor = WorkflowSecurityPredictor(str(rf_model_path))
                logger.info("[SUCCESS] Workflow predictor initialized with trained models")
            else:
                logger.warning("[WARNING] Trained models not found, using fallback mode")
                self.workflow_predictor = None
            
            self.models_loaded = True
            logger.info("[SUCCESS] ML Workflow Scanner fully initialized")
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to initialize ML components: {e}")
            logger.info("🔄 Scanner will run in fallback mode with basic pattern detection")
    
    def _load_trained_models(self):
        """Load the trained ML models from disk."""
        try:
            models_dir = Path(__file__).parent.parent / "ml_scanner" / "models" / "trained_models"
            
            if not models_dir.exists():
                logger.warning(f"Models directory not found: {models_dir}")
                return
            
            # Load Random Forest model (primary)
            rf_path = models_dir / "random_forest_model.joblib"
            if rf_path.exists():
                import joblib
                self.models['random_forest'] = joblib.load(rf_path)
                logger.info("[SUCCESS] Random Forest model loaded")
            
            # Load Logistic Regression model (secondary)
            lr_path = models_dir / "logistic_regression_model.joblib"
            if lr_path.exists():
                import joblib
                self.models['logistic_regression'] = joblib.load(lr_path)
                logger.info("[SUCCESS] Logistic Regression model loaded")
            
            # Load feature names for model input
            features_path = models_dir / "feature_names.txt"
            if features_path.exists():
                with open(features_path, 'r') as f:
                    self.feature_names = [line.strip() for line in f]
                logger.info(f"[SUCCESS] Feature names loaded ({len(self.feature_names)} features)")
            
            if not self.models:
                logger.warning("No trained models found. Using fallback mode.")
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to load trained models: {e}")
    
    async def scan_workflow_content(self, workflow_content: str, workflow_metadata: Dict = None) -> Dict:
        """
        Scan a single workflow YAML content for security vulnerabilities.
        
        Args:
            workflow_content: The YAML content of the workflow
            workflow_metadata: Optional metadata (repo name, path, etc.)
        
        Returns:
            Dict containing security analysis results
        """
        scan_start = datetime.now()
        
        try:
            # Basic validation
            if not workflow_content or not workflow_content.strip():
                return self._create_scan_result(
                    risk_score=0,
                    vulnerabilities=[],
                    status="error",
                    message="Empty workflow content",
                    scan_duration=(datetime.now() - scan_start).total_seconds()
                )
            
            # Use ML models if available, otherwise fallback
            if self.models_loaded and self.models:
                return await self._ml_scan_workflow(workflow_content, workflow_metadata, scan_start)
            else:
                return await self._fallback_scan_workflow(workflow_content, workflow_metadata, scan_start)
                
        except Exception as e:
            logger.error(f"[ERROR] Workflow scan failed: {e}")
            return self._create_scan_result(
                risk_score=50,  # Medium risk for errors
                vulnerabilities=[{
                    "type": "scan_error",
                    "severity": "medium",
                    "message": f"Scan failed: {str(e)}",
                    "recommendation": "Review workflow manually"
                }],
                status="error",
                message=f"Scan error: {str(e)}",
                scan_duration=(datetime.now() - scan_start).total_seconds()
            )
    
    async def _ml_scan_workflow(self, workflow_content: str, metadata: Dict, scan_start: datetime) -> Dict:
        """Scan workflow using ML-based security analysis."""
        try:
            # Use the security analyzer for workflow analysis
            if hasattr(self, 'security_analyzer') and self.security_analyzer:
                # Write workflow content to temporary file for analysis
                import tempfile
                import yaml
                
                with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as temp_file:
                    temp_file.write(workflow_content)
                    temp_file_path = temp_file.name
                
                try:
                    # Analyze the workflow file
                    analysis_result = self.security_analyzer.analyze_workflow(Path(temp_file_path))
                    
                    # Convert security analyzer results to our format
                    risk_score = min(100, max(0, analysis_result.risk_score))
                    
                    vulnerabilities = []
                    for finding in analysis_result.security_findings:
                        vulnerabilities.append({
                            "type": finding.category,
                            "severity": finding.severity.name.lower(),
                            "description": finding.description,
                            "line_number": finding.line_number,
                            "suggestion": finding.suggestion
                        })
                    
                    # Generate ML-based recommendations
                    recommendations = []
                    if vulnerabilities:
                        recommendations.append("Review and remediate identified security issues")
                    if analysis_result.external_actions:
                        recommendations.append("Verify external actions from trusted sources")
                        recommendations.append("Pin action versions to specific commits")
                    if not analysis_result.uses_secrets:
                        recommendations.append("Consider using GitHub Secrets for sensitive data")
                    if analysis_result.permissions:
                        recommendations.append("Review workflow permissions for least privilege")
                    
                    scan_duration = (datetime.now() - scan_start).total_seconds()
                    
                    return {
                        "risk_score": risk_score,
                        "security_findings": vulnerabilities,
                        "recommendations": recommendations,
                        "external_actions": analysis_result.external_actions,
                        "permissions": analysis_result.permissions,
                        "triggers": analysis_result.triggers,
                        "uses_secrets": analysis_result.uses_secrets,
                        "total_jobs": analysis_result.total_jobs,
                        "status": "success",
                        "message": "ML security analysis completed",
                        "scan_duration": scan_duration,
                        "scan_timestamp": scan_start.isoformat(),
                        "metadata": metadata
                    }
                    
                finally:
                    # Clean up temporary file
                    import os
                    try:
                        os.unlink(temp_file_path)
                    except:
                        pass
                        
            else:
                # Fallback to basic pattern detection
                return await self._fallback_scan_workflow(workflow_content, metadata, scan_start)
                
        except Exception as e:
            logger.error(f"ML scan failed: {e}")
            return await self._fallback_scan_workflow(workflow_content, metadata, scan_start)
    
    async def _fallback_scan_workflow(self, workflow_content: str, metadata: Dict, scan_start: datetime) -> Dict:
        """Fallback pattern-based security scan when ML models unavailable."""
        try:
            vulnerabilities = []
            risk_factors = 0
            total_checks = 0
            
            # Pattern-based vulnerability detection
            patterns = {
                "hardcoded_secrets": [
                    r"password\s*[:=]\s*['\"][^'\"]+['\"]",
                    r"token\s*[:=]\s*['\"][^'\"]+['\"]",
                    r"api[_-]?key\s*[:=]\s*['\"][^'\"]+['\"]",
                    r"secret\s*[:=]\s*['\"][^'\"]+['\"]"
                ],
                "privileged_execution": [
                    r"sudo\s+",
                    r"run\s*:\s*.*sudo",
                    r"privileged\s*:\s*true"
                ],
                "external_downloads": [
                    r"curl\s+.*http",
                    r"wget\s+.*http",
                    r"download.*http"
                ],
                "docker_risks": [
                    r"docker\s+run.*--privileged",
                    r"docker.*-u\s+root",
                    r"FROM.*:latest"
                ]
            }
            
            for vuln_type, pattern_list in patterns.items():
                total_checks += len(pattern_list)
                for pattern in pattern_list:
                    import re
                    if re.search(pattern, workflow_content, re.IGNORECASE):
                        risk_factors += 1
                        vulnerabilities.append({
                            "type": vuln_type,
                            "severity": "medium",
                            "pattern": pattern,
                            "message": f"Potential {vuln_type.replace('_', ' ')} detected",
                            "recommendation": f"Review and secure {vuln_type.replace('_', ' ')}"
                        })
            
            # Calculate risk score based on pattern matches
            risk_score = min(100, (risk_factors / max(total_checks, 1)) * 100)
            
            scan_duration = (datetime.now() - scan_start).total_seconds()
            
            return self._create_scan_result(
                risk_score=risk_score,
                vulnerabilities=vulnerabilities,
                status="success",
                message="Pattern-based security scan completed",
                scan_duration=scan_duration,
                patterns_checked=total_checks,
                patterns_matched=risk_factors
            )
            
        except Exception as e:
            logger.error(f"[ERROR] Fallback scan failed: {e}")
            return self._create_scan_result(
                risk_score=25,
                vulnerabilities=[],
                status="partial",
                message="Basic scan completed with limitations",
                scan_duration=(datetime.now() - scan_start).total_seconds()
            )
    
    def _features_to_vector(self, features: Dict) -> List[float]:
        """Convert feature dictionary to vector for ML model input."""
        if not hasattr(self, 'feature_names') or not self.feature_names:
            # Fallback: use basic numeric features
            return [
                features.get('total_steps', 0),
                features.get('uses_actions', 0),
                features.get('has_secrets', 0),
                features.get('external_dependencies', 0),
                features.get('complexity_score', 0)
            ]
        
        # Use trained feature names
        vector = []
        for feature_name in self.feature_names:
            vector.append(features.get(feature_name, 0))
        
        return vector
    
    def _calculate_risk_score(self, probabilities: Dict) -> float:
        """Calculate ensemble risk score from model probabilities."""
        if not probabilities:
            return 0.0
        
        # Weighted ensemble (Random Forest gets higher weight)
        weights = {
            'random_forest': 0.7,
            'logistic_regression': 0.3
        }
        
        weighted_score = 0.0
        total_weight = 0.0
        
        for model_name, prob in probabilities.items():
            weight = weights.get(model_name, 0.5)
            weighted_score += prob * weight
            total_weight += weight
        
        if total_weight > 0:
            weighted_score /= total_weight
        
        # Convert to 0-100 scale
        return min(100, max(0, weighted_score * 100))
    
    def _detect_vulnerability_patterns(self, workflow_content: str, features: Dict) -> List[Dict]:
        """Detect specific vulnerability patterns using feature analysis."""
        vulnerabilities = []
        
        # Use vulnerability injector patterns if available
        if self.vulnerability_injector:
            for vuln_type, pattern_info in self.vulnerability_injector.vulnerability_patterns.items():
                # Check if features indicate this vulnerability type
                if self._check_vulnerability_features(vuln_type, features):
                    vulnerabilities.append({
                        "type": vuln_type,
                        "severity": pattern_info.get("severity", "medium"),
                        "message": pattern_info.get("description", f"{vuln_type} detected"),
                        "recommendation": pattern_info.get("fix", "Review and fix vulnerability")
                    })
        
        return vulnerabilities
    
    def _check_vulnerability_features(self, vuln_type: str, features: Dict) -> bool:
        """Check if features indicate presence of specific vulnerability type."""
        # Map vulnerability types to feature indicators
        vuln_indicators = {
            "hardcoded_secrets": ["has_secrets", "secret_references"],
            "excessive_permissions": ["sudo_usage", "privileged_access"],
            "insecure_downloads": ["external_downloads", "curl_usage"],
            "docker_vulnerabilities": ["docker_usage", "privileged_containers"]
        }
        
        indicators = vuln_indicators.get(vuln_type, [])
        return any(features.get(indicator, 0) > 0 for indicator in indicators)
    
    def _generate_recommendations(self, features: Dict, vulnerabilities: List[Dict]) -> List[str]:
        """Generate security recommendations based on analysis."""
        recommendations = []
        
        # Feature-based recommendations
        if features.get('has_secrets', 0) > 0:
            recommendations.append("Use GitHub Secrets instead of hardcoded credentials")
        
        if features.get('sudo_usage', 0) > 0:
            recommendations.append("Avoid using sudo; use least-privilege principles")
        
        if features.get('external_downloads', 0) > 0:
            recommendations.append("Verify checksums for external downloads")
        
        if features.get('docker_usage', 0) > 0:
            recommendations.append("Use specific image tags instead of 'latest'")
        
        # Vulnerability-specific recommendations
        for vuln in vulnerabilities:
            if "recommendation" in vuln and vuln["recommendation"] not in recommendations:
                recommendations.append(vuln["recommendation"])
        
        return recommendations
    
    def _create_scan_result(self, risk_score: float, vulnerabilities: List[Dict], 
                          status: str, message: str, scan_duration: float, **extra) -> Dict:
        """Create standardized scan result dictionary."""
        return {
            "scan_id": f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "timestamp": datetime.now().isoformat(),
            "status": status,
            "message": message,
            "risk_score": round(risk_score, 2),
            "risk_level": self._get_risk_level(risk_score),
            "vulnerabilities": vulnerabilities,
            "vulnerability_count": len(vulnerabilities),
            "scan_duration_seconds": round(scan_duration, 3),
            "scanner_version": "1.0.0",
            "models_used": list(self.models.keys()) if self.models_loaded else ["fallback"],
            **extra
        }
    
    def _get_risk_level(self, risk_score: float) -> str:
        """Convert numeric risk score to categorical risk level."""
        if risk_score >= 75:
            return "high"
        elif risk_score >= 50:
            return "medium"
        elif risk_score >= 25:
            return "low"
        else:
            return "minimal"
    
    async def scan_repository_workflows(self, org_name: str, repo_name: str, 
                                      github_client, installation_id: int) -> Dict:
        """
        Scan all workflows in a repository.
        
        Args:
            org_name: Organization name
            repo_name: Repository name  
            github_client: GitHub client instance
            installation_id: GitHub App installation ID
        
        Returns:
            Dict containing repository-level scan results
        """
        try:
            # Get all workflows in the repository
            workflows = await github_client.get_repository_workflows(installation_id, org_name, repo_name)
            
            if not workflows:
                return {
                    "repository": f"{org_name}/{repo_name}",
                    "status": "no_workflows",
                    "message": "No workflows found in repository",
                    "scan_results": []
                }
            
            # Scan each workflow
            scan_results = []
            for workflow in workflows:
                try:
                    # Debug: Log workflow structure
                    logger.info(f"[DEBUG] Workflow keys: {list(workflow.keys())}")
                    logger.info(f"[DEBUG] Workflow data: {workflow}")
                    
                    # GitHub API workflow object structure:
                    # - "path" field contains the workflow file path (.github/workflows/filename.yml)
                    # - "html_url" contains browser URL to the file
                    # - "url" contains API URL to the workflow
                    workflow_path = workflow.get('path', '')
                    
                    # If path is empty, try to extract from html_url
                    if not workflow_path and 'html_url' in workflow:
                        html_url = workflow.get('html_url', '')
                        if '.github/workflows/' in html_url:
                            # Extract from: https://github.com/owner/repo/blob/main/.github/workflows/file.yml
                            workflow_path = '.github/workflows/' + html_url.split('.github/workflows/')[-1]
                    
                    # If still no path, try badge_url which might contain the path
                    if not workflow_path and 'badge_url' in workflow:
                        badge_url = workflow.get('badge_url', '')
                        if 'workflow%3A' in badge_url:
                            # Extract workflow name from badge URL and construct path
                            workflow_name = workflow.get('name', 'unknown')
                            workflow_path = f".github/workflows/{workflow_name.lower().replace(' ', '-')}.yml"
                    
                    logger.info(f"[DEBUG] Using workflow path: '{workflow_path}' for '{workflow.get('name')}'")
                    
                    if not workflow_path:
                        logger.error(f"[ERROR] Could not determine workflow path for '{workflow.get('name')}'")
                        scan_results.append({
                            "workflow_name": workflow.get('name'),
                            "workflow_path": "unknown",
                            "status": "error",
                            "message": "Could not determine workflow file path",
                            "risk_score": 0
                        })
                        continue
                    
                    # Get workflow content
                    content = await github_client.get_workflow_content(
                        installation_id, org_name, repo_name, workflow_path
                    )
                    
                    if content and content.strip() and not content.startswith('# Error'):
                        # Scan the workflow
                        scan_result = await self.scan_workflow_content(
                            content,
                            {
                                "repository": f"{org_name}/{repo_name}",
                                "workflow_name": workflow.get('name'),
                                "workflow_path": workflow_path
                            }
                        )
                        scan_result['workflow_name'] = workflow.get('name')
                        scan_result['workflow_path'] = workflow_path
                        scan_results.append(scan_result)
                    else:
                        logger.warning(f"Empty or error content for workflow {workflow.get('name')}")
                        scan_results.append({
                            "workflow_name": workflow.get('name'),
                            "workflow_path": workflow_path,
                            "status": "error",
                            "message": "Failed to fetch workflow content",
                            "risk_score": 0
                        })
                    
                except Exception as e:
                    logger.error(f"Failed to scan workflow {workflow.get('name')}: {e}")
                    # Get workflow path for error reporting
                    error_workflow_path = workflow.get('path') or workflow.get('url', '').split('/')[-1] if workflow.get('url') else 'unknown'
                    scan_results.append({
                        "workflow_name": workflow.get('name'),
                        "workflow_path": error_workflow_path,
                        "status": "error",
                        "message": f"Scan failed: {str(e)}",
                        "risk_score": 0
                    })
            
            # Calculate repository-level metrics
            total_workflows = len(scan_results)
            successful_scans = len([r for r in scan_results if r.get('status') == 'success'])
            avg_risk_score = sum(r.get('risk_score', 0) for r in scan_results) / max(total_workflows, 1)
            high_risk_workflows = len([r for r in scan_results if r.get('risk_score', 0) >= 75])
            
            return {
                "repository": f"{org_name}/{repo_name}",
                "status": "success",
                "message": f"Scanned {successful_scans}/{total_workflows} workflows",
                "scan_results": scan_results,
                "repository_metrics": {
                    "total_workflows": total_workflows,
                    "successful_scans": successful_scans,
                    "average_risk_score": round(avg_risk_score, 2),
                    "high_risk_workflows": high_risk_workflows,
                    "scan_coverage": round((successful_scans / max(total_workflows, 1)) * 100, 1)
                }
            }
            
        except Exception as e:
            logger.error(f"Repository scan failed for {org_name}/{repo_name}: {e}")
            return {
                "repository": f"{org_name}/{repo_name}",
                "status": "error",
                "message": f"Repository scan failed: {str(e)}",
                "scan_results": []
            }

# Global scanner instance
ml_scanner = MLWorkflowScanner()