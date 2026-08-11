from sqlalchemy.orm import Session
from fastapi import HTTPException
from starlette import status
from src.serving import schemas
from src.serving.repository import ModelRepository, ModelVersionRepository

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