import time
from sqlalchemy.orm import Session
from fastapi import HTTPException
from starlette import status

from src.serving import schemas
from src.serving.repository import ModelRepository, ModelVersionRepository
from src.serving.storage import ArtifactNotFoundError
from src.serving.loader import SklearnJoblibLoader, UnsupportedModelFormat
from src.serving.cache import model_cache
from src.serving.dependency import get_artifact_storage
from src.serving.observability import Observability

# ==========================================
# Custom Exceptions
# ==========================================
class ArchivedModelError(Exception):
    pass

class InvalidFeatures(Exception):
    pass

class PredictionError(Exception):
    pass


# ==========================================
# Services
# ==========================================
class ModelService:
    @staticmethod
    def create_model(db: Session, model_data: schemas.ModelCreate):
        existing_model = ModelRepository.get_model_by_name(db, model_data.name)
        if existing_model:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Model with name '{model_data.name}' already exists."
            )
        return ModelRepository.create_model(db, model_data)

    @staticmethod
    def get_all_models(db: Session):
        return ModelRepository.get_all_models(db)

    @staticmethod
    def get_model_by_name(db: Session, model_name: str):
        model = ModelRepository.get_model_by_name(db, model_name)
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model '{model_name}' not found."
            )
        return model


class ModelVersionService:
    @staticmethod
    def create_version(db: Session, model_name: str, version_data: schemas.ModelVersionCreate):
        model = ModelService.get_model_by_name(db, model_name)

        existing_version = ModelVersionRepository.get_version_by_model_and_name(db, model.id, version_data.version)
        if existing_version:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Version '{version_data.version}' already exists for model '{model_name}'."
            )

        return ModelVersionRepository.create_model_version(db, model.id, version_data)

    @staticmethod
    def get_versions(db: Session, model_name: str):
        model = ModelService.get_model_by_name(db, model_name)
        return ModelVersionRepository.get_versions_by_model(db, model.id)

    @staticmethod
    def load_model_version(db: Session, model_name: str, version: str) -> dict:
        # 1. بررسی کش
        if model_cache.contains(model_name, version):
            Observability.record_cache_hit(model_name, version)
            return {"model_name": model_name, "version": version, "status": "already_loaded"}

        Observability.record_cache_miss(model_name, version)

        # 2. بررسی وجود مدل
        model = ModelService.get_model_by_name(db, model_name)
        model_version = ModelVersionRepository.get_version_by_model_and_name(db, model.id, version)

        if not model_version:
            raise HTTPException(status_code=404, detail="Version not found")

        if model_version.status == "archived":
            raise ArchivedModelError("Cannot load archived model version")

        if model_version.framework != "scikit-learn" or model_version.model_format != "joblib":
            raise UnsupportedModelFormat("Unsupported format")

        # 3. لود مدل و ثبت زمان
        storage = get_artifact_storage()
        try:
            start_time = time.time()
            artifact_bytes = storage.get(model_version.artifact_uri)
            loader = SklearnJoblibLoader()
            loaded_model = loader.load(artifact_bytes)
            load_latency = time.time() - start_time

            Observability.record_model_load(model_name, version, "success", load_latency)
        except ArtifactNotFoundError:
            Observability.record_model_load(model_name, version, "error")
            raise ArtifactNotFoundError(f"Artifact missing for URI: {model_version.artifact_uri}")
        except Exception as e:
            Observability.record_model_load(model_name, version, "error")
            raise e

        # 4. ذخیره در کش
        model_cache.set(model_name, version, loaded_model)
        return {"model_name": model_name, "version": version, "status": "loaded"}

    @staticmethod
    def get_model_status(model_name: str, version: str) -> dict:
        is_loaded = model_cache.contains(model_name, version)
        return {
            "model_name": model_name,
            "version": version,
            "loaded": is_loaded
        }


class PredictionService:
    @staticmethod
    def predict(db: Session, model_name: str, version: str, features: list[float]) -> dict:

        # --- اصلاح نهایی: فقط Hit را اینجا ثبت می‌کنیم، Miss درون متد load ثبت می‌شود ---
        if model_cache.contains(model_name, version):
            Observability.record_cache_hit(model_name, version)
        else:
            ModelVersionService.load_model_version(db, model_name, version)
        # ------------------------------------------------------------------------------

        model = model_cache.get(model_name, version)
        if not model:
            raise PredictionError("Model is not available in memory")

        if hasattr(model, "n_features_in_") and len(features) != model.n_features_in_:
            raise InvalidFeatures(f"Expected {model.n_features_in_} features, got {len(features)}.")

        try:
            start_pred_time = time.time()
            prediction_result = model.predict([features])
            prediction_latency = time.time() - start_pred_time

            val = prediction_result[0].item() if hasattr(prediction_result[0], "item") else prediction_result[0]

            Observability.record_prediction_success(model_name, version, prediction_latency)
            return {"model_name": model_name, "version": version, "prediction": val}

        except Exception as e:
            raise PredictionError(f"Prediction failed: {str(e)}")