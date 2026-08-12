from sqlalchemy.orm import Session
from fastapi import HTTPException
from starlette import status
from src.serving import schemas
from src.serving.repository import ModelRepository, ModelVersionRepository
from src.serving.storage import ArtifactNotFoundError
from src.serving.loader import SklearnJoblibLoader, UnsupportedModelFormat
from src.serving.cache import model_cache
from src.serving.dependency import get_artifact_storage

class InvalidFeatures(Exception):
    pass
class PredictionError(Exception):
    pass


class ArchivedModelError(Exception):
    pass

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
        """
        Complete management of loading a model from storage to memory (MSP-004)
        """
        # 1. Check if the model exists
        model = ModelService.get_model_by_name(db, model_name)

        # 2. Check if the version exists
        model_version = ModelVersionRepository.get_version_by_model_and_name(db, model.id, version)
        if not model_version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Version '{version}' not found for model '{model_name}'."
            )

        # 3. Apply lifecycle management rules
        if model_version.status == "archived":
            raise ArchivedModelError(f"Cannot load archived model version: {model_name}:{version}")

        # 4. Check cache (has it already been loaded?)
        if model_cache.contains(model_name, version):
            return {"model_name": model_name, "version": version, "status": "already_loaded"}

        # 5. Validate supported format
        if model_version.framework != "scikit-learn" or model_version.model_format != "joblib":
            raise UnsupportedModelFormat(
                f"Unsupported format: {model_version.framework}/{model_version.model_format}"
            )

        # 6. Retrieve model file bytes from the Storage Layer
        storage = get_artifact_storage()
        try:
            artifact_bytes = storage.get(model_version.artifact_uri)
        except ArtifactNotFoundError:
            raise ArtifactNotFoundError(f"Artifact missing for URI: {model_version.artifact_uri}")

        # 7. Load the bytes as a model into Memory
        loader = SklearnJoblibLoader()
        loaded_model = loader.load(artifact_bytes)

        # 8. Save in Cache for future requests
        model_cache.set(model_name, version, loaded_model)

        return {"model_name": model_name, "version": version, "status": "loaded"}

    @staticmethod
    def get_model_status(model_name: str, version: str) -> dict:
        """
        Check the load status of a model in the Cache
        """
        is_loaded = model_cache.contains(model_name, version)
        return {
            "model_name": model_name,
            "version": version,
            "loaded": is_loaded
        }


class PredictionService:
    @staticmethod
    def predict(db: Session, model_name: str, version: str, features: list[float]) -> dict:
        # 1. Is the model in the Cache? If not, load it (Auto-loading)
        if not model_cache.contains(model_name, version):
            # The load_model_version method performs all checks (model existence, version, archived status, and finding the file)
            ModelVersionService.load_model_version(db, model_name, version)

        # 2. Retrieve the model from the Cache
        model = model_cache.get(model_name, version)
        if not model:
            raise PredictionError("Model is not available in memory after load attempt.")

        # 3. Feature Count Validation
        # Many Scikit-Learn models have the n_features_in_ attribute
        if hasattr(model, "n_features_in_"):
            expected_features = model.n_features_in_
            if len(features) != expected_features:
                raise InvalidFeatures(
                    f"Invalid number of features. Expected {expected_features}, got {len(features)}."
                )

        # 4. Execute prediction
        try:
            # Scikit-Learn expects a 2D array (a list of lists)
            prediction_result = model.predict([features])

            # Extract the first result (since we only sent one record)
            prediction_value = prediction_result[0]

            # Convert NumPy values to standard Python types (for JSON serialization)
            if hasattr(prediction_value, "item"):
                prediction_value = prediction_value.item()

            return {
                "model_name": model_name,
                "version": version,
                "prediction": prediction_value
            }
        except Exception as e:
            raise PredictionError(f"Error during model prediction: {str(e)}")