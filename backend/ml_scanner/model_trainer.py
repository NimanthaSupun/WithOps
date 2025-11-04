"""
Simple ML Model Trainer for Workflow Security Classification

Trains basic ML models on the extracted workflow features.
"""

import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix
from sklearn.preprocessing import StandardScaler
import pickle

def load_dataset():
    """Load the prepared ML dataset"""
    data_dir = Path("data/ml_dataset")
    
    if not data_dir.exists():
        print("❌ Dataset not found! Run dataset_builder.py first.")
        return None, None, None, None
    
    # Load train/test split
    X_train = np.load(data_dir / "X_train.npy")
    X_test = np.load(data_dir / "X_test.npy") 
    y_train = np.load(data_dir / "y_train.npy")
    y_test = np.load(data_dir / "y_test.npy")
    
    print(f"✅ Dataset loaded:")
    print(f"  Training samples: {len(X_train)}")
    print(f"  Test samples: {len(X_test)}")
    print(f"  Features: {X_train.shape[1]}")
    
    return X_train, X_test, y_train, y_test

def train_models(X_train, X_test, y_train, y_test):
    """Train and evaluate ML models"""
    
    print("\n🤖 Training ML Models...")
    print("=" * 40)
    
    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    models = {
        'Random Forest': RandomForestClassifier(n_estimators=100, random_state=42),
        'Logistic Regression': LogisticRegression(random_state=42, max_iter=1000)
    }
    
    results = {}
    
    for name, model in models.items():
        print(f"\nTraining {name}...")
        
        # Train model
        model.fit(X_train_scaled, y_train)
        
        # Predict
        y_pred = model.predict(X_test_scaled)
        
        # Evaluate
        accuracy = accuracy_score(y_test, y_pred)
        
        print(f"  Accuracy: {accuracy:.3f}")
        
        results[name] = {
            'model': model,
            'accuracy': accuracy,
            'predictions': y_pred
        }
        
        # Save model
        model_path = Path("data/ml_dataset") / f"{name.lower().replace(' ', '_')}_model.pkl"
        with open(model_path, 'wb') as f:
            pickle.dump({'model': model, 'scaler': scaler}, f)
        print(f"  Model saved to: {model_path}")
    
    return results

def main():
    """Main training pipeline"""
    print("🚀 ML Model Training Pipeline")
    print("=" * 50)
    
    # Load dataset
    X_train, X_test, y_train, y_test = load_dataset()
    
    if X_train is None:
        return
    
    # Train models
    results = train_models(X_train, X_test, y_train, y_test)
    
    # Summary
    print(f"\n" + "=" * 50)
    print("📊 TRAINING RESULTS SUMMARY")
    print("=" * 50)
    
    for name, result in results.items():
        print(f"{name}: {result['accuracy']:.3f} accuracy")
    
    best_model = max(results.items(), key=lambda x: x[1]['accuracy'])
    print(f"\n🏆 Best model: {best_model[0]} ({best_model[1]['accuracy']:.3f})")
    
    print(f"\n✅ ML models trained and saved!")
    print(f"📁 Models saved in: data/ml_dataset/")
    print(f"🎯 Ready for workflow security prediction!")

if __name__ == "__main__":
    main()