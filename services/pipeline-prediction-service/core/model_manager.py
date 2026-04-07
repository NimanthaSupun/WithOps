"""
Model Manager for Pipeline Prediction Service

Handles saving, loading, versioning, and lifecycle management of
trained ML models. Models are persisted as .joblib files on disk
and registered in the ml_model_registry database table.
"""

import os
import logging
import joblib
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

MODELS_DIR = os.getenv("MODELS_DIR", "./models")


class ModelManager:
    """
    Manages ML model lifecycle:
    - Save trained models to disk (.joblib)
    - Load models from disk into memory
    - Track model versions in database
    - Keep one active model per organization
    """

    def __init__(self):
        self.models_dir = MODELS_DIR
        self._loaded_models: Dict[str, Any] = {}  # org_name -> model object
        self._model_metadata: Dict[str, Dict] = {}  # org_name -> metadata
        os.makedirs(self.models_dir, exist_ok=True)

    async def save_model(
        self,
        model: Any,
        org_name: str,
        model_type: str,
        metrics: Dict[str, float],
        feature_importance: Dict[str, float],
        feature_names: List[str],
        training_samples: int,
        class_distribution: Dict[str, int],
    ) -> int:
        """
        Save a trained model to disk and register it in the database.

        Args:
            model: Trained sklearn/xgboost model object
            org_name: Organization the model was trained for
            model_type: "random_forest" or "xgboost"
            metrics: Dict with accuracy, precision, recall, f1, auc_roc
            feature_importance: Dict of feature_name -> importance_score
            feature_names: List of feature column names
            training_samples: Number of samples used for training
            class_distribution: e.g. {"success": 800, "failure": 200}

        Returns:
            model_version: The version number of the saved model
        """
        # Determine next version number
        version = await self._get_next_version(org_name)

        # Save model to disk
        filename = f"model_{org_name}_v{version}.joblib"
        filepath = os.path.join(self.models_dir, filename)
        joblib.dump(model, filepath)
        logger.info(f"💾 Model saved to {filepath}")

        # Register in database
        await self._register_model(
            org_name=org_name,
            version=version,
            model_type=model_type,
            metrics=metrics,
            feature_importance=feature_importance,
            feature_names=feature_names,
            training_samples=training_samples,
            class_distribution=class_distribution,
            model_path=filepath,
        )

        # Load into memory cache
        self._loaded_models[org_name] = model
        self._model_metadata[org_name] = {
            "version": version,
            "model_type": model_type,
            "metrics": metrics,
            "feature_importance": feature_importance,
            "feature_names": feature_names,
            "trained_at": datetime.utcnow().isoformat(),
        }

        logger.info(f"✅ Model v{version} for {org_name} saved and loaded into memory")
        return version

    def get_model(self, org_name: str) -> Optional[Any]:
        """Get the loaded model for an organization."""
        return self._loaded_models.get(org_name)

    def get_metadata(self, org_name: str) -> Optional[Dict]:
        """Get metadata for the loaded model."""
        return self._model_metadata.get(org_name)

    def is_model_loaded(self, org_name: str) -> bool:
        """Check if a model is loaded for the given organization."""
        return org_name in self._loaded_models

    def get_active_model_count(self) -> int:
        """Get the number of models currently loaded in memory."""
        return len(self._loaded_models)

    async def load_model_from_disk(self, org_name: str) -> bool:
        """
        Load the latest active model for an organization from disk.
        Returns True if successfully loaded, False otherwise.
        """
        try:
            metadata = await self._get_active_model_metadata(org_name)
            if not metadata:
                logger.warning(f"⚠️ No active model found for {org_name}")
                return False

            filepath = metadata.get("model_path")
            if not filepath or not os.path.exists(filepath):
                logger.error(f"❌ Model file not found: {filepath}")
                return False

            model = joblib.load(filepath)
            self._loaded_models[org_name] = model
            self._model_metadata[org_name] = metadata
            logger.info(f"✅ Loaded model v{metadata['version']} for {org_name}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to load model for {org_name}: {e}")
            return False

    async def load_all_active_models(self):
        """Load all active models from database into memory on startup."""
        try:
            from database.config import db_manager
            from database.models import MLModelRegistry
            from sqlalchemy import select

            async with db_manager.get_session() as session:
                result = await session.execute(
                    select(MLModelRegistry)
                    .where(MLModelRegistry.is_active == True)
                )
                active_models = result.scalars().all()

                loaded = 0
                for record in active_models:
                    if record.model_path and os.path.exists(record.model_path):
                        try:
                            model = joblib.load(record.model_path)
                            self._loaded_models[record.org_name] = model
                            self._model_metadata[record.org_name] = {
                                "version": record.model_version,
                                "model_type": record.model_type,
                                "metrics": {
                                    "accuracy": record.accuracy,
                                    "precision": record.precision_score,
                                    "recall": record.recall_score,
                                    "f1": record.f1_score,
                                    "auc_roc": record.auc_roc,
                                },
                                "feature_importance": record.feature_importance or {},
                                "feature_names": record.feature_names or [],
                                "trained_at": record.trained_at.isoformat() if record.trained_at else None,
                            }
                            loaded += 1
                        except Exception as e:
                            logger.error(f"❌ Failed to load model for {record.org_name}: {e}")

                logger.info(f"✅ Loaded {loaded} active model(s) into memory")

        except Exception as e:
            logger.error(f"❌ Error loading active models: {e}")

    # ════════════════════════════════════════════════════════════════════════
    # DATABASE HELPERS
    # ════════════════════════════════════════════════════════════════════════

    async def _get_next_version(self, org_name: str) -> int:
        """Get the next model version number for an organization."""
        from database.config import db_manager
        from database.models import MLModelRegistry
        from sqlalchemy import select, func

        async with db_manager.get_session() as session:
            result = await session.execute(
                select(func.max(MLModelRegistry.model_version))
                .where(MLModelRegistry.org_name == org_name)
            )
            max_version = result.scalar()
            return (max_version or 0) + 1

    async def _register_model(self, org_name: str, version: int,
                               model_type: str, metrics: Dict,
                               feature_importance: Dict,
                               feature_names: List[str],
                               training_samples: int,
                               class_distribution: Dict,
                               model_path: str):
        """Register a trained model in the database."""
        from database.config import db_manager
        from database.models import MLModelRegistry
        from sqlalchemy import update

        async with db_manager.get_session() as session:
            # Deactivate previous models for this org
            await session.execute(
                update(MLModelRegistry)
                .where(MLModelRegistry.org_name == org_name)
                .where(MLModelRegistry.is_active == True)
                .values(is_active=False)
            )

            # Insert new model record
            record = MLModelRegistry(
                org_name=org_name,
                model_version=version,
                model_type=model_type,
                training_samples=training_samples,
                feature_count=len(feature_names),
                feature_names=feature_names,
                accuracy=metrics.get("accuracy"),
                precision_score=metrics.get("precision"),
                recall_score=metrics.get("recall"),
                f1_score=metrics.get("f1"),
                auc_roc=metrics.get("auc_roc"),
                confusion_matrix=metrics.get("confusion_matrix"),
                feature_importance=feature_importance,
                model_path=model_path,
                is_active=True,
                class_distribution=class_distribution,
            )
            session.add(record)
            await session.commit()

            logger.info(f"📋 Model v{version} registered in database for {org_name}")

    async def _get_active_model_metadata(self, org_name: str) -> Optional[Dict]:
        """Get metadata for the active model from the database."""
        from database.config import db_manager
        from database.models import MLModelRegistry
        from sqlalchemy import select

        async with db_manager.get_session() as session:
            result = await session.execute(
                select(MLModelRegistry)
                .where(MLModelRegistry.org_name == org_name)
                .where(MLModelRegistry.is_active == True)
            )
            record = result.scalar()

            if not record:
                return None

            return {
                "version": record.model_version,
                "model_type": record.model_type,
                "model_path": record.model_path,
                "metrics": {
                    "accuracy": record.accuracy,
                    "precision": record.precision_score,
                    "recall": record.recall_score,
                    "f1": record.f1_score,
                    "auc_roc": record.auc_roc,
                },
                "feature_importance": record.feature_importance or {},
                "feature_names": record.feature_names or [],
                "trained_at": record.trained_at.isoformat() if record.trained_at else None,
            }


# Global instance
model_manager = ModelManager()
