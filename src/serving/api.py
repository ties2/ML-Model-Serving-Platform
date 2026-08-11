from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from src.serving import schemas
from src.serving.database import get_db
from src.serving.service import ModelService, ModelVersionService

router = APIRouter(prefix="/models", tags=["Model Registry"])

# Endpoints for Models
@router.post("", response_model=schemas.ModelResponse)
def create_model(model_data: schemas.ModelCreate, db: Session = Depends(get_db)):
    return ModelService.create_model(db, model_data)

@router.get("", response_model=List[schemas.ModelResponse])
def get_all_models(db: Session = Depends(get_db)):
    return ModelService.get_all_models(db)

@router.get("/{model_name}", response_model=schemas.ModelResponse)
def get_model(model_name: str, db: Session = Depends(get_db)):
    return ModelService.get_model_by_name(db, model_name)


# Endpoints for Model Versions

@router.post("/{model_name}/versions", response_model=schemas.ModelVersionResponse)
def create_model_version(
        model_name: str,
        version_data: schemas.ModelVersionCreate,
        db: Session = Depends(get_db)
):

    return ModelVersionService.create_version(db, model_name, version_data)

@router.get("/{model_name}/versions", response_model=List[schemas.ModelVersionResponse])
def get_model_versions(model_name: str, db: Session = Depends(get_db)):

    return ModelVersionService.get_versions(db, model_name)