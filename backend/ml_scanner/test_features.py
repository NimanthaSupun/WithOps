"""
Simple test for ML feature extraction
"""

from pathlib import Path
from feature_extractor import WorkflowFeatureExtractor

def simple_test():
    print("🧪 Testing Feature Extraction...")
    
    # Initialize extractor
    extractor = WorkflowFeatureExtractor()
    
    # Find one workflow file to test
    data_dir = Path("data/workflows")
    workflow_files = list(data_dir.glob("*.yml"))
    
    if not workflow_files:
        print("❌ No workflow files found!")
        return
    
    # Test on first file
    test_file = workflow_files[0]
    print(f"Testing on: {test_file.name}")
    
    try:
        features = extractor.extract_features(test_file)
        
        print(f"✅ Features extracted successfully!")
        print(f"  - Jobs: {features.job_count}")
        print(f"  - Steps: {features.step_count}")
        print(f"  - Uses secrets: {features.uses_secrets}")
        print(f"  - External actions: {features.external_action_count}")
        print(f"  - Risk score: {features.risk_score:.1f}/100")
        
        # Test multiple files
        print(f"\nTesting on 5 files:")
        for i, file_path in enumerate(workflow_files[:5]):
            features = extractor.extract_features(file_path)
            print(f"  {i+1}. {file_path.name[:25]:<25} Risk: {features.risk_score:5.1f}/100")
        
        print(f"\n✅ Feature extraction pipeline working!")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    simple_test()