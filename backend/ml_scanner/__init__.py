"""
ML Scanner Package

This package contains the machine learning components for workflow security analysis.
"""

# Import main classes for easier access
try:
    from .feature_extractor import WorkflowFeatureExtractor
    from .security_analyzer import WorkflowSecurityAnalyzer
    from .workflow_predictor import WorkflowSecurityPredictor
    
    __all__ = [
        'WorkflowFeatureExtractor',
        'WorkflowSecurityAnalyzer', 
        'WorkflowSecurityPredictor'
    ]
except ImportError as e:
    # Graceful handling if dependencies are missing
    import logging
    logging.warning(f"Some ML scanner components could not be imported: {e}")
    __all__ = []