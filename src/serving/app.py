import uuid
from fastapi import FastAPI, Request
from fastapi.responses import Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from src.serving.database import engine, Base
from src.serving.api import router as models_router
from src.serving.observability import Observability

Base.metadata.create_all(bind=engine)

app = FastAPI(title="MLOps Serving API")
app.include_router(models_router)

import uuid
from fastapi import FastAPI, Request
from fastapi.responses import Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from src.serving.api import router as models_router
from src.serving.database import engine, Base
from src.serving.observability import Observability

# Create database tables (if you are not using Alembic)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="ML Model Serving Platform")

# Middleware for generating and registering Request ID
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    # If the client sent an X-Request-ID header, use it; otherwise, generate a new one
    req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

    # Save in the context to be used in the logger without needing to pass it through methods
    Observability.set_request_id(req_id)

    response = await call_next(request)

    # Return the ID in the response headers (for client debugging)
    response.headers["X-Request-ID"] = req_id
    return response

# Standard metrics endpoint for Prometheus
@app.get("/metrics", tags=["Observability"])
def get_metrics():
    """Standard Prometheus-compatible output"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}

app.include_router(models_router)

# @app.get("/health")
# def health_check():
#     return {"status": "ok"}