"""
ML Dataset Builder

Creates a complete training dataset from workflow files for machine learning models.
Exports data in formats ready for scikit-learn, pandas, and other ML frameworks.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Tuple
import json
import pickle
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from feature_extractor import WorkflowFeatureExtractor, WorkflowFeatures
import logging

logger = logging.getLogger(__name__)

class MLDatasetBuilder:
    """Builds ML-ready datasets from workflow features"""
    
    def __init__(self, data_dir: Path = None):
        self.data_dir = data_dir or Path("data/workflows")
        self.extractor = WorkflowFeatureExtractor()
        self.scaler = StandardScaler()
        self.features_df = None
        self.X = None  # Feature matrix
        self.y = None  # Labels (risk categories)
        
    def build_dataset(self, max_files: int = None) -> pd.DataFrame:
        """
        Build complete dataset from all workflow files.
        
        Args:
            max_files: Maximum number of files to process (None for all)
            
        Returns:
            DataFrame with extracted features
        """
        print("🏗️  Building ML Dataset...")
        print("=" * 50)
        
        # Find all workflow files
        workflow_files = list(self.data_dir.glob("*.yml")) + list(self.data_dir.glob("*.yaml"))
        
        if max_files:
            workflow_files = workflow_files[:max_files]
        
        print(f"Processing {len(workflow_files)} workflow files...")
        
        # Extract features from all files
        feature_list = []
        successful_extractions = 0
        
        for i, file_path in enumerate(workflow_files):
            if i % 50 == 0:  # Progress update every 50 files
                print(f"  Progress: {i}/{len(workflow_files)} files processed...")
            
            try:
                features = self.extractor.extract_features(file_path)
                feature_list.append(features)
                successful_extractions += 1
            except Exception as e:
                logger.error(f"Failed to extract features from {file_path}: {e}")
                continue
        
        print(f"✅ Successfully extracted features from {successful_extractions}/{len(workflow_files)} files")
        
        # Convert to DataFrame
        self.features_df = self._features_to_dataframe(feature_list)
        
        # Create feature matrix and labels
        self.X, self.y = self._prepare_ml_data(self.features_df)
        
        return self.features_df
    
    def _features_to_dataframe(self, feature_list: List[WorkflowFeatures]) -> pd.DataFrame:
        """Convert list of WorkflowFeatures to pandas DataFrame"""
        
        # Convert features to dictionary format
        data_rows = []
        for features in feature_list:
            row = {}
            for field_name in WorkflowFeatures.__dataclass_fields__:
                row[field_name] = getattr(features, field_name)
            data_rows.append(row)
        
        df = pd.DataFrame(data_rows)
        
        # Convert boolean columns to integers for ML
        bool_columns = df.select_dtypes(include=['bool']).columns
        df[bool_columns] = df[bool_columns].astype(int)
        
        return df
    
    def _prepare_ml_data(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare feature matrix X and label vector y for ML"""
        
        # Exclude filename from features
        feature_columns = [col for col in df.columns if col != 'filename']
        X = df[feature_columns].values
        
        # Create risk category labels from risk_score
        y = self._create_risk_labels(df['risk_score'].values)
        
        return X, y
    
    def _create_risk_labels(self, risk_scores: np.ndarray) -> np.ndarray:
        """Convert risk scores to categorical labels"""
        labels = []
        for score in risk_scores:
            if score < 10:
                labels.append('low')
            elif score < 30:
                labels.append('medium') 
            elif score < 60:
                labels.append('high')
            else:
                labels.append('critical')
        
        # Convert to numeric labels
        label_encoder = LabelEncoder()
        return label_encoder.fit_transform(labels)
    
    def get_train_test_split(self, test_size: float = 0.2, random_state: int = 42) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Get train/test split of the dataset"""
        if self.X is None or self.y is None:
            raise ValueError("Dataset not built yet. Call build_dataset() first.")
        
        # Check if we can use stratified split
        unique_labels, counts = np.unique(self.y, return_counts=True)
        min_count = counts.min()
        
        # Use stratified split only if all classes have at least 2 samples
        if min_count >= 2:
            return train_test_split(self.X, self.y, test_size=test_size, random_state=random_state, stratify=self.y)
        else:
            # Use regular split without stratification
            print(f"⚠️  Warning: Some classes have only {min_count} sample(s). Using non-stratified split.")
            return train_test_split(self.X, self.y, test_size=test_size, random_state=random_state)
    
    def get_scaled_features(self) -> np.ndarray:
        """Get standardized feature matrix"""
        if self.X is None:
            raise ValueError("Dataset not built yet. Call build_dataset() first.")
        
        return self.scaler.fit_transform(self.X)
    
    def save_dataset(self, output_dir: Path = None):
        """Save dataset to multiple formats"""
        if output_dir is None:
            output_dir = Path("data/ml_dataset")
        
        output_dir.mkdir(exist_ok=True)
        
        print(f"💾 Saving dataset to {output_dir}...")
        
        # Save DataFrame as CSV and pickle
        self.features_df.to_csv(output_dir / "workflow_features.csv", index=False)
        self.features_df.to_pickle(output_dir / "workflow_features.pkl")
        
        # Save numpy arrays
        np.save(output_dir / "X_features.npy", self.X)
        np.save(output_dir / "y_labels.npy", self.y)
        
        # Save train/test split
        X_train, X_test, y_train, y_test = self.get_train_test_split()
        np.save(output_dir / "X_train.npy", X_train)
        np.save(output_dir / "X_test.npy", X_test)
        np.save(output_dir / "y_train.npy", y_train)
        np.save(output_dir / "y_test.npy", y_test)
        
        # Save scaled features
        X_scaled = self.get_scaled_features()
        np.save(output_dir / "X_scaled.npy", X_scaled)
        
        # Save metadata
        metadata = {
            'total_samples': len(self.features_df),
            'feature_count': self.X.shape[1] if self.X is not None else 0,
            'feature_names': [col for col in self.features_df.columns if col != 'filename'],
            'risk_distribution': self.features_df['risk_score'].describe().to_dict(),
            'class_distribution': {str(k): int(v) for k, v in zip(*np.unique(self.y, return_counts=True))} if self.y is not None else {}
        }
        
        with open(output_dir / "metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"✅ Dataset saved with {len(self.features_df)} samples and {self.X.shape[1]} features")
    
    def generate_analysis_report(self) -> Dict[str, Any]:
        """Generate comprehensive analysis report of the dataset"""
        if self.features_df is None:
            raise ValueError("Dataset not built yet. Call build_dataset() first.")
        
        df = self.features_df
        
        report = {
            'dataset_summary': {
                'total_workflows': len(df),
                'feature_count': len([col for col in df.columns if col != 'filename']),
                'average_risk_score': float(df['risk_score'].mean()),
                'max_risk_score': float(df['risk_score'].max()),
                'min_risk_score': float(df['risk_score'].min())
            },
            
            'security_insights': {
                'workflows_using_secrets': int(df['uses_secrets'].sum()),
                'workflows_with_external_actions': int((df['external_action_count'] > 0).sum()),
                'workflows_with_write_permissions': int((df['write_permission_count'] > 0).sum()),
                'workflows_with_dangerous_triggers': int((df['dangerous_trigger_count'] > 0).sum()),
                'workflows_with_hardcoded_secrets': int((df['hardcoded_secret_count'] > 0).sum())
            },
            
            'complexity_insights': {
                'average_jobs_per_workflow': float(df['job_count'].mean()),
                'average_steps_per_workflow': float(df['step_count'].mean()),
                'workflows_with_matrix_jobs': int((df['matrix_job_count'] > 0).sum()),
                'workflows_with_conditional_steps': int((df['conditional_step_count'] > 0).sum()),
                'max_external_actions': int(df['external_action_count'].max())
            },
            
            'risk_distribution': {
                'low_risk': int((df['risk_score'] < 10).sum()),
                'medium_risk': int(((df['risk_score'] >= 10) & (df['risk_score'] < 30)).sum()),
                'high_risk': int(((df['risk_score'] >= 30) & (df['risk_score'] < 60)).sum()),
                'critical_risk': int((df['risk_score'] >= 60).sum())
            },
            
            'top_risk_factors': self._identify_top_risk_factors(df)
        }
        
        return report
    
    def _identify_top_risk_factors(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Identify the top risk factors in the dataset"""
        risk_factors = {}
        
        # Correlation with risk score
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        correlations = df[numeric_columns].corr()['risk_score'].abs().sort_values(ascending=False)
        
        # Top features correlated with risk
        top_risk_features = correlations.head(10).to_dict()
        risk_factors['features_correlated_with_risk'] = {
            k: float(v) for k, v in top_risk_features.items() if k != 'risk_score'
        }
        
        # Most common security issues
        security_issues = {
            'external_actions_usage': float((df['external_action_count'] > 0).mean()),
            'secrets_usage': float(df['uses_secrets'].mean()),
            'write_permissions_usage': float((df['write_permission_count'] > 0).mean()),
            'unpinned_actions_ratio': float(df['unpinned_action_ratio'].mean())
        }
        risk_factors['common_security_issues'] = security_issues
        
        return risk_factors

def main():
    """Build and analyze the complete ML dataset"""
    print("🚀 Building Complete ML Dataset")
    print("=" * 60)
    
    # Initialize dataset builder
    builder = MLDatasetBuilder()
    
    # Build dataset (process all workflow files)
    df = builder.build_dataset(max_files=50)  # Start with 50 files for demo
    
    if df is None or len(df) == 0:
        print("❌ Failed to build dataset")
        return
    
    # Generate analysis report
    print("\n📊 Generating Analysis Report...")
    report = builder.generate_analysis_report()
    
    # Print summary
    print("\n" + "=" * 60)
    print("📈 DATASET ANALYSIS SUMMARY")
    print("=" * 60)
    
    summary = report['dataset_summary']
    print(f"Total workflows: {summary['total_workflows']}")
    print(f"Features extracted: {summary['feature_count']}")
    print(f"Average risk score: {summary['average_risk_score']:.1f}/100")
    
    print(f"\n🔒 Security Insights:")
    security = report['security_insights']
    print(f"  Workflows using secrets: {security['workflows_using_secrets']}")
    print(f"  Workflows with external actions: {security['workflows_with_external_actions']}")
    print(f"  Workflows with write permissions: {security['workflows_with_write_permissions']}")
    print(f"  Workflows with hardcoded secrets: {security['workflows_with_hardcoded_secrets']}")
    
    print(f"\n⚡ Complexity Insights:")
    complexity = report['complexity_insights']
    print(f"  Average jobs per workflow: {complexity['average_jobs_per_workflow']:.1f}")
    print(f"  Average steps per workflow: {complexity['average_steps_per_workflow']:.1f}")
    print(f"  Workflows with matrix jobs: {complexity['workflows_with_matrix_jobs']}")
    
    print(f"\n🚨 Risk Distribution:")
    risk_dist = report['risk_distribution']
    print(f"  Low risk (0-10): {risk_dist['low_risk']}")
    print(f"  Medium risk (10-30): {risk_dist['medium_risk']}")
    print(f"  High risk (30-60): {risk_dist['high_risk']}")
    print(f"  Critical risk (60+): {risk_dist['critical_risk']}")
    
    # Save dataset
    print(f"\n💾 Saving dataset...")
    builder.save_dataset()
    
    # Save analysis report
    with open("data/ml_dataset/analysis_report.json", 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n✅ ML Dataset Build Complete!")
    print(f"📁 Files saved to: data/ml_dataset/")
    print(f"🎯 Ready for ML model training!")

if __name__ == "__main__":
    main()