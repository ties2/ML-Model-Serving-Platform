from fastapi import APIRouter, Depends, HTTPException ,status
from sqlalchemy.orm import Session
from typing import List
from src.serving import schemas
from src.serving.database import get_db
from src.serving.service import ModelService, ModelVersionService, ArchivedModelError
from src.serving.storage import ArtifactNotFoundError
from src.serving.loader import (
    UnsupportedModelFormat,
    InvalidModelArtifact,
    ModelLoadError
)

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

#  Endpoints for Model Loader
@router.post("/{model_name}/versions/{version}/load")
def load_model(model_name: str, version: str, db: Session = Depends(get_db)):
    """
    Endpoint to load a model from Storage into Memory
    """
    try:
        result = ModelVersionService.load_model_version(db, model_name, version)
        return result

    except ArchivedModelError as e:
        # 409 Conflict status code for when the operation conflicts with the current state of the resource (archived model)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    except ArtifactNotFoundError as e:
        # 404 Not Found status code
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    except (UnsupportedModelFormat, InvalidModelArtifact) as e:
        # 400 Bad Request status code for when the file format is incorrect or the file is invalid
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    except ModelLoadError as e:
        # 500 Internal Server Error status code for unexpected errors during model loading
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    # Note: Errors related to the model or version not being found are already handled in the service with a 404 code


@router.get("/{model_name}/versions/{version}/status")
def get_model_status(model_name: str, version: str):
    """
    Endpoint to view the current status of the model in the Cache
    """
    # This method doesn't need the database because it reads directly from RAM (Cache)
    result = ModelVersionService.get_model_status(model_name, version)
    return result