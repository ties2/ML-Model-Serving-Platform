from fastapi import FastAPI
from src.serving.database import engine, Base
from src.serving.api import router as models_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="MLOps Serving API")

app.include_router(models_router)

@app.get("/health")
def health_check():
    return {"status": "ok"}