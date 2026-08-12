from src.serving.config import settings
from src.serving.storage import LocalArtifactStorage, ArtifactStorage

def get_artifact_storage() -> ArtifactStorage:
    if settings.ARTIFACT_STORAGE_BACKEND == "local": #or change config to use "s3"
        return LocalArtifactStorage(base_dir=settings.ARTIFACT_STORAGE_BACKEND)
    raise ValueError(f"Unsupported storage backend: {settings.ARTIFACT_STORAGE_BACKEND}")