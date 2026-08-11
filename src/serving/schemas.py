#validation data

from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

# Schemas for Model Version
class ModelVersionCreate(BaseModel):
    version: str
    framework: str
    model_format: str
    artifact_uri: str
    status: str = "staging"

class ModelVersionResponse(ModelVersionCreate):
    id: int
    model_id: int
    created_at:datetime

    #allo to pydantic that read data directly from SQLAlchemy
    model_config = ConfigDict(from_attributes=True)

# Schemas for Model Registry
class ModelCreate(BaseModel):
    name: str
    description: Optional[str] = None

class ModelResponse(ModelCreate):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
