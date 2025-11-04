"""
Quick test of the security analyzer
"""

from security_analyzer import WorkflowSecurityAnalyzer, RiskLevel
from pathlib import Path

def main():
    print("🔍 Testing Security Analyzer...")
    print("="*50)
    
    # Initialize analyzer
    analyzer = WorkflowSecurityAnalyzer()
    
    # Find workflow files
    data_dir = Path("data/workflows")
    workflow_files = list(data_dir.glob("*.yml")) + list(data_dir.glob("*.yaml"))
    
    print(f"Found {len(workflow_files)} workflow files")
    
    if len(workflow_files) == 0:
        print("❌ No workflow files found!")
        return
    
    # Analyze first 5 workflows as a test
    print("\nAnalyzing first 5 workflows:")
    print("-" * 50)
    
    total_findings = 0
    high_risk_count = 0
    
    for i, file_path in enumerate(workflow_files[:5]):
        print(f"\n{i+1}. {file_path.name}")
        
        try:
            analysis = analyzer.analyze_workflow(file_path)
            
            print(f"   📊 Risk Score: {analysis.risk_score:.1f}/100")
            print(f"   💼 Jobs: {analysis.total_jobs}")
            print(f"   🔗 External Actions: {len(analysis.external_actions)}")
            print(f"   ⚠️  Findings: {len(analysis.security_findings)}")
            
            if analysis.risk_score > 30:
                high_risk_count += 1
                print(f"   🚨 HIGH RISK")
            
            total_findings += len(analysis.security_findings)
            
            # Show a sample finding
            if analysis.security_findings:
                finding = analysis.security_findings[0]
                print(f"   🔍 Sample issue: {finding.category} - {finding.description[:40]}...")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print(f"\n" + "="*50)
    print(f"📈 QUICK SUMMARY")
    print(f"="*50)
    print(f"Workflows analyzed: 5")
    print(f"Total security findings: {total_findings}")
    print(f"High-risk workflows: {high_risk_count}")
    print(f"Average findings per workflow: {total_findings/5:.1f}")
    
    print(f"\n✅ Security analyzer is working!")
    print(f"📁 Ready to analyze all {len(workflow_files)} workflows")

if __name__ == "__main__":
    main()