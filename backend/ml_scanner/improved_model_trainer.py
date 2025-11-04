"""
Improved ML Model Trainer for Balanced Dataset

Trains ML models on the balanced dataset with both clean and vulnerable workflows.
This should significantly improve model accuracy and real-world performance.
"""

import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import pickle

def load_balanced_dataset():
    """Load the balanced dataset with clean and vulnerable workflows"""
    data_dir = Path("data/balanced_dataset")
    
    if not data_dir.exists():
        print("❌ Balanced dataset not found! Run balanced_dataset_builder.py first.")
        return None, None
    
    # Load dataset
    df = pd.read_csv(data_dir / "balanced_workflow_dataset.csv")
    
    # Separate features and labels
    feature_columns = [col for col in df.columns if col not in ['filename', 'is_vulnerable', 'vulnerability_type']]
    X = df[feature_columns].values
    y = df['is_vulnerable'].values
    
    print(f"✅ Balanced dataset loaded:")
    print(f"  Total samples: {len(df)}")
    print(f"  Features: {len(feature_columns)}")
    print(f"  Clean workflows: {(y == 0).sum()}")
    print(f"  Vulnerable workflows: {(y == 1).sum()}")
    print(f"  Balance ratio: {(y == 1).mean():.1%}")
    
    return X, y

def train_improved_models(X, y):
    """Train and evaluate ML models on balanced dataset"""
    
    print("\n🚀 Training Models on Balanced Dataset...")
    print("=" * 50)
    
    # Split dataset
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"Training set: {len(X_train)} samples")
    print(f"Test set: {len(X_test)} samples")
    
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
        print(f"\n🤖 Training {name}...")
        
        # Train model
        model.fit(X_train_scaled, y_train)
        
        # Predictions
        y_pred = model.predict(X_test_scaled)
        y_prob = model.predict_proba(X_test_scaled)[:, 1]
        
        # Evaluate
        accuracy = accuracy_score(y_test, y_pred)
        auc_score = roc_auc_score(y_test, y_prob)
        
        print(f"  Accuracy: {accuracy:.3f}")
        print(f"  AUC Score: {auc_score:.3f}")
        
        # Detailed classification report
        print(f"\n  Classification Report:")
        print(classification_report(y_test, y_pred, target_names=['Clean', 'Vulnerable']))
        
        # Confusion matrix
        cm = confusion_matrix(y_test, y_pred)
        print(f"\n  Confusion Matrix:")
        print(f"  True Negatives (Clean→Clean): {cm[0,0]}")
        print(f"  False Positives (Clean→Vulnerable): {cm[0,1]}")
        print(f"  False Negatives (Vulnerable→Clean): {cm[1,0]}")
        print(f"  True Positives (Vulnerable→Vulnerable): {cm[1,1]}")
        
        results[name] = {
            'model': model,
            'scaler': scaler,
            'accuracy': accuracy,
            'auc_score': auc_score,
            'predictions': y_pred,
            'probabilities': y_prob
        }
        
        # Save improved model
        model_path = Path("data/balanced_dataset") / f"{name.lower().replace(' ', '_')}_balanced_model.pkl"
        with open(model_path, 'wb') as f:
            pickle.dump({'model': model, 'scaler': scaler}, f)
        print(f"  Model saved to: {model_path}")
    
    return results

def compare_with_original():
    """Compare performance with original unbalanced model"""
    print("\n📊 PERFORMANCE COMPARISON")
    print("=" * 50)
    
    # Load original model results (if available)
    original_data_dir = Path("data/ml_dataset")
    if original_data_dir.exists():
        print("Original (Unbalanced) Dataset:")
        try:
            with open(original_data_dir / "metadata.json", 'r') as f:
                original_meta = __import__('json').load(f)
            print(f"  Samples: {original_meta.get('total_samples', 'N/A')}")
            print(f"  Expected performance: Low (biased toward 'clean' predictions)")
        except:
            print("  Original metadata not available")
    
    # Load balanced model results
    balanced_data_dir = Path("data/balanced_dataset")
    if balanced_data_dir.exists():
        print("\nBalanced Dataset:")
        try:
            with open(balanced_data_dir / "metadata.json", 'r') as f:
                balanced_meta = __import__('json').load(f)
            print(f"  Samples: {balanced_meta.get('total_samples', 'N/A')}")
            print(f"  Clean: {balanced_meta.get('clean_samples', 'N/A')}")
            print(f"  Vulnerable: {balanced_meta.get('vulnerable_samples', 'N/A')}")
            print(f"  Balance: {balanced_meta.get('balance_ratio', 0):.1%}")
            print("  Expected performance: High (learns both secure and vulnerable patterns)")
        except:
            print("  Balanced metadata not available")

def main():
    """Main training pipeline for balanced dataset"""
    print("⚖️  Improved ML Training with Balanced Dataset")
    print("=" * 60)
    
    # Load balanced dataset
    X, y = load_balanced_dataset()
    
    if X is None:
        return
    
    # Train models
    results = train_improved_models(X, y)
    
    # Compare with original
    compare_with_original()
    
    # Summary
    print(f"\n" + "=" * 60)
    print("🏆 TRAINING RESULTS SUMMARY")
    print("=" * 60)
    
    for name, result in results.items():
        print(f"{name}:")
        print(f"  Accuracy: {result['accuracy']:.3f}")
        print(f"  AUC Score: {result['auc_score']:.3f}")
    
    best_model = max(results.items(), key=lambda x: x[1]['auc_score'])
    print(f"\n🥇 Best model: {best_model[0]} (AUC: {best_model[1]['auc_score']:.3f})")
    
    print(f"\n✅ Improved ML models trained on balanced dataset!")
    print(f"📁 Models saved in: data/balanced_dataset/")
    print(f"🎯 Much better performance expected on real-world workflows!")

if __name__ == "__main__":
    main()