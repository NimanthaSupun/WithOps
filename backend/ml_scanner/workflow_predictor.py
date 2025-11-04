"""
Workflow Security Predictor

Complete end-to-end pipeline for predicting security risk of GitHub Actions workflows.
Uses trained ML models to classify new workflow files.
"""

import pickle
import numpy as np
from pathlib import Path
from typing import Dict, Any, Tuple, List
from feature_extractor import WorkflowFeatureExtractor, WorkflowFeatures

class WorkflowSecurityPredictor:
    """Complete workflow security prediction system"""
    
    def __init__(self, model_path: str = None):
        """
        Initialize the predictor with a trained model.
        
        Args:
            model_path: Path to saved model file. If None, uses Random Forest model.
        """
        if model_path is None:
            model_path = "data/ml_dataset/random_forest_model.pkl"
        
        self.model_path = Path(model_path)
        self.feature_extractor = WorkflowFeatureExtractor()
        self.model = None
        self.scaler = None
        
        # Risk level mapping
        self.risk_levels = {0: 'low', 1: 'medium', 2: 'high', 3: 'critical'}
        
        # Load trained model
        self._load_model()
    
    def _load_model(self):
        """Load the trained ML model and scaler"""
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model file not found: {self.model_path}")
        
        with open(self.model_path, 'rb') as f:
            model_data = pickle.load(f)
            self.model = model_data['model']
            self.scaler = model_data['scaler']
        
        print(f"✅ Model loaded from: {self.model_path}")
    
    def predict_workflow(self, workflow_path: Path) -> Dict[str, Any]:
        """
        Predict security risk for a single workflow file.
        
        Args:
            workflow_path: Path to workflow YAML file
            
        Returns:
            Dictionary with prediction results
        """
        # Extract features
        features = self.feature_extractor.extract_features(workflow_path)
        
        # Convert features to array (exclude filename)
        feature_vector = self._features_to_array(features)
        
        # Scale features
        feature_vector_scaled = self.scaler.transform([feature_vector])
        
        # Predict
        prediction = self.model.predict(feature_vector_scaled)[0]
        probabilities = self.model.predict_proba(feature_vector_scaled)[0]
        
        # Get confidence (max probability)
        confidence = float(np.max(probabilities))
        
        return {
            'filename': features.filename,
            'risk_category': self.risk_levels[prediction],
            'risk_score': features.risk_score,
            'confidence': confidence,
            'ml_prediction': int(prediction),
            'probabilities': {
                level: float(prob) for level, prob in zip(self.risk_levels.values(), probabilities)
            },
            'key_features': self._extract_key_features(features),
            'recommendations': self._generate_recommendations(features)
        }
    
    def _features_to_array(self, features: WorkflowFeatures) -> np.ndarray:
        """Convert WorkflowFeatures to numpy array"""
        # Get all feature values except filename
        feature_values = []
        for field_name in WorkflowFeatures.__dataclass_fields__:
            if field_name != 'filename':
                value = getattr(features, field_name)
                # Convert boolean to int
                if isinstance(value, bool):
                    value = int(value)
                feature_values.append(value)
        
        return np.array(feature_values)
    
    def _extract_key_features(self, features: WorkflowFeatures) -> Dict[str, Any]:
        """Extract most important features for explanation"""
        return {
            'jobs': features.job_count,
            'steps': features.step_count,
            'uses_secrets': features.uses_secrets,
            'external_actions': features.external_action_count,
            'write_permissions': features.write_permission_count,
            'dangerous_triggers': features.dangerous_trigger_count,
            'hardcoded_secrets': features.hardcoded_secret_count,
            'unpinned_actions_ratio': round(features.unpinned_action_ratio, 2)
        }
    
    def _generate_recommendations(self, features: WorkflowFeatures) -> List[str]:
        """Generate security recommendations based on features"""
        recommendations = []
        
        if features.hardcoded_secret_count > 0:
            recommendations.append("🔒 Use GitHub secrets instead of hardcoded credentials")
        
        if features.external_action_count > 2:
            recommendations.append("🔗 Review external actions for trustworthiness")
        
        if features.unpinned_action_ratio > 0.5:
            recommendations.append("📌 Pin actions to specific versions or commit hashes")
        
        if features.write_permission_count > 2:
            recommendations.append("⚠️  Review write permissions - use minimum required")
        
        if features.dangerous_trigger_count > 0:
            recommendations.append("🚨 Be cautious with pull_request_target triggers")
        
        if features.curl_wget_count > 0:
            recommendations.append("🌐 Validate external downloads and scripts")
        
        if not recommendations:
            recommendations.append("✅ Workflow follows good security practices")
        
        return recommendations

def main():
    """Demo the workflow security predictor"""
    print("🔮 Workflow Security Predictor Demo")
    print("=" * 50)
    
    # Initialize predictor
    try:
        predictor = WorkflowSecurityPredictor()
    except FileNotFoundError as e:
        print(f"❌ {e}")
        print("Run model_trainer.py first to train models.")
        return
    
    # Find workflow files to test
    workflow_dir = Path("data/workflows")
    workflow_files = list(workflow_dir.glob("*.yml"))[:5]  # Test first 5
    
    if not workflow_files:
        print("❌ No workflow files found for testing")
        return
    
    print(f"Testing predictor on {len(workflow_files)} workflow files...\n")
    
    for i, workflow_path in enumerate(workflow_files):
        print(f"🔍 Analyzing: {workflow_path.name}")
        print("-" * 40)
        
        try:
            result = predictor.predict_workflow(workflow_path)
            
            print(f"📊 Risk Category: {result['risk_category'].upper()}")
            print(f"📈 Risk Score: {result['risk_score']:.1f}/100")
            print(f"🎯 ML Confidence: {result['confidence']:.2f}")
            
            print(f"🔧 Key Features:")
            for key, value in result['key_features'].items():
                print(f"   {key}: {value}")
            
            print(f"💡 Recommendations:")
            for rec in result['recommendations']:
                print(f"   {rec}")
            
            print()
            
        except Exception as e:
            print(f"❌ Error analyzing {workflow_path.name}: {e}")
            print()
    
    print("✅ Prediction demo complete!")
    print("🚀 Workflow security predictor is ready for production use!")

if __name__ == "__main__":
    main()