#script for define tables of database

from datetime import UTC, datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import relationship

from src.serving.database import Base


class DBModel(Base):
    __tablename__ = 'models'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    versions = relationship("DBModelVersion", back_populates="model", cascade="all, delete-orphan")

class DBModelVersion(Base):
    __tablename__ = 'model_versions'
    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(Integer, ForeignKey("models.id"), nullable=False)
    version = Column(String, nullable=False)
    framework = Column(String, nullable=False)
    model_format = Column(String, nullable=False)
    artifact_uri = Column(String, nullable=False)
    status = Column(String, nullable=False, default="staging")
    created_at = Column(DateTime, default=datetime.now(UTC))

    model = relationship("DBModel", back_populates="versions")

    __table_args__ = (
        UniqueConstraint('model_id', 'version', name='_model_version_uc'),
        Index(
            'uix_model_production',
            'model_id',
            unique=True,
            postgresql_where=text("status = 'production'")
        ),
    )
