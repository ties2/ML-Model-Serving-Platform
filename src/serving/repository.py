from sqlalchemy.orm import Session
from src.serving import db_models, schemas

class ModelRepository:

    @staticmethod
    def get_model_by_name(db: Session, name: str):
        return db.query(db_models.DBModel).filter(db_models.DBModel.name == name).first()

    @staticmethod
    def get_all_models(db: Session):
        return db.query(db_models.DBModel).all()

    @staticmethod
    def create_model(db: Session, model_data: schemas.ModelCreate):
        db_model = db_models.DBModel(
            name=model_data.name,
            description=model_data.description
        )
        db.add(db_model)
        db.commit()
        db.refresh(db_model)
        return db_model


class ModelVersionRepository:

    @staticmethod
    def get_version_by_model_and_name(db: Session, model_id: int, version: str):
        return db.query(db_models.DBModelVersion).filter(
            db_models.DBModelVersion.model_id == model_id,
            db_models.DBModelVersion.version == version
        ).first()

    @staticmethod
    def get_versions_by_model(db: Session, model_id: int):
        return db.query(db_models.DBModelVersion).filter(
            db_models.DBModelVersion.model_id == model_id
        ).all()

    @staticmethod
    def create_model_version(db: Session, model_id: int, version_data: schemas.ModelVersionCreate):
        db_version = db_models.DBModelVersion(
            model_id=model_id,
            version=version_data.version,
            framework=version_data.framework,
            model_format=version_data.model_format,
            artifact_uri=version_data.artifact_uri,
            status=version_data.status
        )
        db.add(db_version)
        db.commit()
        db.refresh(db_version)
        return db_version