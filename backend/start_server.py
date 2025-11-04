#!/usr/bin/env python3
"""
Startup script for the DevSecOps backend with vulnerability prediction
"""

import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and run the app
if __name__ == "__main__":
    import uvicorn
    from main import app
    
    print("🚀 Starting DevSecOps Backend with Vulnerability Prediction")
    print("=" * 60)
    
    # Test that all ML components can be imported
    try:
        import xgboost
        import lightgbm
        import sklearn
        print("✅ All ML dependencies available")
        
        # Test that our ML modules can be imported
        from ml.vulnerability_predictor import VulnerabilityPredictor
        from ml.feature_extractor import FeatureExtractor
        print("✅ ML components imported successfully")
        
        # Test API routes
        from api.routes.vulnerability_prediction import router
        print("✅ Vulnerability prediction routes available")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        sys.exit(1)
    
    print("\n🎯 Starting server on http://127.0.0.1:8001")
    print("📖 API Documentation: http://127.0.0.1:8001/docs")
    print("🔧 Vulnerability Prediction: http://127.0.0.1:8001/docs#/vulnerability-prediction")
    
    # Start the server
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8001,  # Use port 8001 instead
        reload=False,  # Disable reload to avoid issues
        log_level="info"
    )