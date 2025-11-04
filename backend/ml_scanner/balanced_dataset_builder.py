"""
Balanced Dataset Builder

Creates a balanced training dataset by combining clean workflows 
with synthetically generated vulnerable variants, ensuring the ML model
learns to distinguish between secure and insecure patterns.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Tuple
import json
from feature_extractor import WorkflowFeatureExtractor, WorkflowFeatures
from vulnerability_injector import VulnerabilityInjector
import logging

logger = logging.getLogger(__name__)

class BalancedDatasetBuilder:
    """Builds balanced datasets with both secure and vulnerable workflows"""
    
    def __init__(self):
        self.feature_extractor = WorkflowFeatureExtractor()
        self.vulnerability_injector = VulnerabilityInjector()
        
    def create_balanced_dataset(self, clean_dir: Path, max_clean_files: int = 50) -> pd.DataFrame:
        """
        Create a balanced dataset with both clean and vulnerable workflows.
        
        Args:
            clean_dir: Directory containing clean workflow files
            max_clean_files: Maximum number of clean files to process
            
        Returns:
            Balanced DataFrame with features and labels
        """
        print("🏗️  Creating Balanced Dataset...")
        print("=" * 50)
        
        # Step 1: Process clean workflows
        clean_features = self._extract_clean_features(clean_dir, max_clean_files)
        print(f"✅ Extracted features from {len(clean_features)} clean workflows")
        
        # Step 2: Create vulnerable variants
        vulnerable_dir = Path("data/vulnerable_workflows")
        self._create_vulnerable_variants(clean_dir, vulnerable_dir, max_clean_files)
        
        # Step 3: Extract features from vulnerable workflows
        vulnerable_features = self._extract_vulnerable_features(vulnerable_dir)
        print(f"✅ Extracted features from {len(vulnerable_features)} vulnerable workflows")
        
        # Step 4: Combine and label the dataset
        balanced_df = self._combine_and_label_features(clean_features, vulnerable_features)
        
        print(f"\n📊 Dataset Balance:")
        print(f"Total samples: {len(balanced_df)}")
        print(f"Clean workflows: {len(clean_features)} ({len(clean_features)/len(balanced_df)*100:.1f}%)")
        print(f"Vulnerable workflows: {len(vulnerable_features)} ({len(vulnerable_features)/len(balanced_df)*100:.1f}%)")
        
        return balanced_df
    
    def _extract_clean_features(self, clean_dir: Path, max_files: int) -> List[WorkflowFeatures]:
        """Extract features from clean workflow files"""
        clean_files = list(clean_dir.glob("*.yml"))[:max_files]
        
        clean_features = []
        for file_path in clean_files:
            try:
                features = self.feature_extractor.extract_features(file_path)
                clean_features.append(features)
            except Exception as e:
                logger.error(f"Error extracting features from {file_path}: {e}")
        
        return clean_features
    
    def _create_vulnerable_variants(self, clean_dir: Path, vulnerable_dir: Path, max_files: int):
        """Create vulnerable variants from clean workflows"""
        vulnerable_dir.mkdir(exist_ok=True)
        
        # Check if vulnerable variants already exist
        existing_vulnerable = list(vulnerable_dir.glob("*.yml"))
        if len(existing_vulnerable) > 0:
            print(f"Found {len(existing_vulnerable)} existing vulnerable variants")
            return
        
        print("Creating vulnerable variants...")
        clean_files = list(clean_dir.glob("*.yml"))[:max_files]
        
        total_created = 0
        for clean_file in clean_files:
            variants = self.vulnerability_injector.create_vulnerable_variants(
                clean_file, vulnerable_dir, variants_per_file=2
            )
            total_created += len(variants)
        
        print(f"Created {total_created} vulnerable variants")
    
    def _extract_vulnerable_features(self, vulnerable_dir: Path) -> List[WorkflowFeatures]:
        """Extract features from vulnerable workflow files"""
        vulnerable_files = list(vulnerable_dir.glob("*.yml"))
        
        vulnerable_features = []
        for file_path in vulnerable_files:
            try:
                features = self.feature_extractor.extract_features(file_path)
                vulnerable_features.append(features)
            except Exception as e:
                logger.error(f"Error extracting features from {file_path}: {e}")
        
        return vulnerable_features
    
    def _combine_and_label_features(self, clean_features: List[WorkflowFeatures], 
                                   vulnerable_features: List[WorkflowFeatures]) -> pd.DataFrame:
        """Combine clean and vulnerable features with appropriate labels"""
        
        all_features = []
        all_labels = []
        
        # Add clean workflows (label = 0 for secure)
        for features in clean_features:
            feature_dict = self._features_to_dict(features)
            feature_dict['is_vulnerable'] = 0
            feature_dict['vulnerability_type'] = 'clean'
            all_features.append(feature_dict)
            all_labels.append(0)
        
        # Add vulnerable workflows (label = 1 for vulnerable)
        for features in vulnerable_features:
            feature_dict = self._features_to_dict(features)
            feature_dict['is_vulnerable'] = 1
            feature_dict['vulnerability_type'] = 'synthetic'
            all_features.append(feature_dict)
            all_labels.append(1)
        
        # Create DataFrame
        df = pd.DataFrame(all_features)
        
        # Convert boolean columns to integers
        bool_columns = df.select_dtypes(include=['bool']).columns
        df[bool_columns] = df[bool_columns].astype(int)
        
        return df
    
    def _features_to_dict(self, features: WorkflowFeatures) -> Dict[str, Any]:
        """Convert WorkflowFeatures to dictionary"""
        feature_dict = {}
        for field_name in WorkflowFeatures.__dataclass_fields__:
            feature_dict[field_name] = getattr(features, field_name)
        return feature_dict
    
    def save_balanced_dataset(self, df: pd.DataFrame, output_dir: Path = None):
        """Save the balanced dataset"""
        if output_dir is None:
            output_dir = Path("data/balanced_dataset")
        
        output_dir.mkdir(exist_ok=True)
        
        # Save main dataset
        df.to_csv(output_dir / "balanced_workflow_dataset.csv", index=False)
        df.to_pickle(output_dir / "balanced_workflow_dataset.pkl")
        
        # Prepare feature matrix and labels
        feature_columns = [col for col in df.columns if col not in ['filename', 'is_vulnerable', 'vulnerability_type']]
        X = df[feature_columns].values
        y = df['is_vulnerable'].values
        
        # Save as numpy arrays
        np.save(output_dir / "X_balanced.npy", X)
        np.save(output_dir / "y_balanced.npy", y)
        
        # Save metadata
        metadata = {
            'total_samples': len(df),
            'feature_count': len(feature_columns),
            'feature_names': feature_columns,
            'clean_samples': int((df['is_vulnerable'] == 0).sum()),
            'vulnerable_samples': int((df['is_vulnerable'] == 1).sum()),
            'balance_ratio': float((df['is_vulnerable'] == 1).mean()),
            'vulnerability_distribution': {
                'hardcoded_secrets': int((df['hardcoded_secret_count'] > 0).sum()),
                'external_actions': int((df['external_action_count'] > 0).sum()),
                'write_permissions': int((df['write_permission_count'] > 0).sum()),
                'dangerous_triggers': int((df['dangerous_trigger_count'] > 0).sum())
            }
        }
        
        with open(output_dir / "metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"✅ Balanced dataset saved to: {output_dir}")
        print(f"📊 Dataset summary:")
        print(f"   Total samples: {metadata['total_samples']}")
        print(f"   Clean: {metadata['clean_samples']}")
        print(f"   Vulnerable: {metadata['vulnerable_samples']}")
        print(f"   Balance ratio: {metadata['balance_ratio']:.1%}")
    
    def analyze_balance_quality(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze the quality of the balanced dataset"""
        
        clean_df = df[df['is_vulnerable'] == 0]
        vuln_df = df[df['is_vulnerable'] == 1]
        
        analysis = {
            'balance_metrics': {
                'total_samples': len(df),
                'clean_samples': len(clean_df),
                'vulnerable_samples': len(vuln_df),
                'balance_ratio': len(vuln_df) / len(df),
                'ideal_balance': abs(0.5 - (len(vuln_df) / len(df))) < 0.1
            },
            
            'feature_distributions': {
                'avg_risk_score_clean': float(clean_df['risk_score'].mean()),
                'avg_risk_score_vulnerable': float(vuln_df['risk_score'].mean()),
                'risk_score_separation': float(vuln_df['risk_score'].mean() - clean_df['risk_score'].mean())
            },
            
            'vulnerability_coverage': {
                'secrets_coverage': int((vuln_df['hardcoded_secret_count'] > 0).sum()),
                'permissions_coverage': int((vuln_df['write_permission_count'] > 0).sum()),
                'external_actions_coverage': int((vuln_df['external_action_count'] > 0).sum()),
                'triggers_coverage': int((vuln_df['dangerous_trigger_count'] > 0).sum())
            }
        }
        
        return analysis

def main():
    """Create balanced dataset for ML training"""
    print("⚖️  Balanced Dataset Creation Pipeline")
    print("=" * 60)
    
    # Initialize builder
    builder = BalancedDatasetBuilder()
    
    # Create balanced dataset
    clean_dir = Path("data/workflows")
    balanced_df = builder.create_balanced_dataset(clean_dir, max_clean_files=30)
    
    # Analyze balance quality
    analysis = builder.analyze_balance_quality(balanced_df)
    
    print(f"\n📈 BALANCE QUALITY ANALYSIS")
    print("=" * 60)
    
    balance = analysis['balance_metrics']
    print(f"Balance ratio: {balance['balance_ratio']:.1%}")
    print(f"Is well balanced: {'✅' if balance['ideal_balance'] else '❌'}")
    
    features = analysis['feature_distributions'] 
    print(f"\nRisk score separation:")
    print(f"  Clean workflows: {features['avg_risk_score_clean']:.1f}/100")
    print(f"  Vulnerable workflows: {features['avg_risk_score_vulnerable']:.1f}/100")
    print(f"  Separation gap: {features['risk_score_separation']:.1f} points")
    
    coverage = analysis['vulnerability_coverage']
    print(f"\nVulnerability coverage:")
    print(f"  Hardcoded secrets: {coverage['secrets_coverage']} workflows")
    print(f"  Write permissions: {coverage['permissions_coverage']} workflows")
    print(f"  External actions: {coverage['external_actions_coverage']} workflows")
    print(f"  Dangerous triggers: {coverage['triggers_coverage']} workflows")
    
    # Save balanced dataset
    builder.save_balanced_dataset(balanced_df)
    
    print(f"\n✅ Balanced dataset creation complete!")
    print(f"🎯 Ready for improved ML model training!")

if __name__ == "__main__":
    main()