```markdown
# ML Model Serving Platform (MSP)

A production-grade infrastructure for registering, versioning, and serving machine learning models at scale. This architecture strictly decouples data processing, model training, deployment, and monitoring, ensuring high maintainability and scalability.

## Architecture & Tech Stack

- **API Layer:** FastAPI, Pydantic, Python 3.12
- **Observability:** Prometheus Client, Structured Logging, ContextVars
- **Experiment Tracking:** MLflow
- **Data Versioning:** DVC (Data Version Control)
- **Linting & Formatting:** Ruff (managed via pre-commit hooks)
- **Infrastructure & CI/CD:** Docker, GitHub Actions, Make


## Current Status & Features

**CURRENTLY IMPLEMENTED:**
* ✅ **FastAPI Base Setup:** Core application structure.
* ✅ **Health Check:** `GET /health` endpoint working.
* ✅ **Dockerization:** Containerized via Docker & Docker Compose (including local volumes for DB and model artifacts).
* ✅ **Database:** PostgreSQL container configured and connected.
* ✅ **Model Registry:** PostgreSQL-backed model and version metadata tracking (MSP-002).
* ✅ **Artifact Storage:** Storage abstraction with Local backend support, URI resolution (`local://`), and path traversal protection (MSP-003).
* ✅ **Model Loader & Cache:** Abstraction for loading Sklearn/joblib models from bytes with in-memory caching and lifecycle validation (MSP-004).
* ✅ **Prediction API:** End-to-end real-time inference with auto-loading, feature-count validation, and robust error handling (MSP-005).
* ✅ **Observability:** Prometheus-compatible metrics (`/metrics`), structured JSON logging (without PII), and dynamic Request IDs (MSP-006).
* ✅ **Testing:** Comprehensive unit and integration tests (47 tests) running in Docker.

**PLANNED FOR FUTURE RELEASES (MLOps Scope):**
* 🚧 Production Monitoring (Prometheus Server & Grafana Dashboards)
* 🚧 Model Versioning & Experiment Tracking (MLflow, DVC)
* 🚧 Model Monitoring & Drift Detection
* 🚧 CI/CD Pipelines (GitHub Actions)


## Quick Start (Local Development)

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/yourusername/ml-serving-platform.git](https://github.com/yourusername/ml-serving-platform.git)
   cd ml-serving-platform

```

2. **Set up environment variables:**
   Our Makefile handles the creation of the .venv directory and the installation of all requirements automatically
```bash
# Creates .venv, upgrades pip, and installs requirements.txt
make

# Activate the virtual environment
source .venv/bin/activate

```


3. **Set up environment variables:**
```bash
cp env.example .env

```


4. **Start the infrastructure:**
```bash
docker compose up --build -d

```


5. **Verify health:**
```bash
uvicorn src.serving.app:app --host 0.0.0.0 --port 8000 --reload

curl http://localhost:8000/health
http://localhost:8000/docs

```


*Expected Response:* `{"status": "ok"}`

## Core API Endpoints

Once the application is running, the interactive API documentation is available at `http://localhost:8000/docs`.

### Model Registry

* `POST /models` - Register a new ML model.
* `POST /models/{model_name}/versions` - Register a new version.
* `GET /models/{model_name}` - Retrieve model metadata and active versions.

### Model Management

* `POST /{model_name}/versions/{version}/load` - Load a model artifact into memory explicitly.
* `GET /{model_name}/versions/{version}/status` - Check if a model is currently loaded in memory cache.

### Inference

* `POST /{model_name}/versions/{version}/predict` - Run real-time inference against the active model (auto-loads if not in cache).
```json
{
  "features": [0.2, 1.5, 10.0, 3.2]
}

```


*Expected Response:*
```json
{
  "model_name": "fraud-model",
  "version": "1.0.0",
  "prediction": 1
}

```



### Observability

* `GET /metrics` - Exposes Prometheus-compatible metrics for monitoring systems.

## troubleshooting

```bash
#restart docker
docker compose down
docker compose up -d 

#build api
docker compose build --no-cache api
docker compose build api

#create build again
docker compose build
docker compose up -d

#cleaning cache (Fix for missing artifacts or build bugs)
docker builder prune -a -f
docker system prune -f

```

## Running Tests

Tests are executed inside an isolated container to ensure environment consistency. We allocate 2GB of shared memory to prevent `Bus error` crashes during heavy Numpy/Joblib operations on macOS environments.

```bash
docker compose run --rm --shm-size=2gb api pytest -v

docker compose run --rm  api pytest -v

docker compose exec api python -m pytest -v
```

## Project Structure

```text
ml-serving-platform/
│
├── .github/
│   └── workflows/
│       └── ci-cd.yaml              # CI/CD Pipeline (Lint, Test, Build)
│
├── data/                           # Tracked by DVC, ignored by Git
│   ├── raw.dvc                     #
│   └── processed.dvc               #
│
├── deployment/
│   └── Dockerfile                  # Containerization for FastAPI serving
│
├── dvc/                            # DVC config for data versioning
│
├── logs/                           # Auto-generated by custom logger
│   ├── webapp.log                  
│   └── training.log                
│
├── src/                            # Main source code package
│   ├── __init__.py                 
│   ├── data_generation/            # Ingestion scripts
│   ├── features/                   # Feature engineering pipeline
│   ├── models/                     # ML models domain
│   │   ├── train.py                # MLflow training pipeline
│   │   └── evaluate.py             # Offline evaluation
│   ├── monitoring/                 # Post-deployment checks
│   │   └── drift_detector.py       # Data and concept drift checks
│   ├── serving/                    # API domain (replaces your app/api)
│   │   ├── api.py                  # API router & endpoints
│   │   ├── app.py                  # FastAPI application
│   │   ├── cache.py                # In-memory model caching
│   │   ├── config.py               # Environment configuration
│   │   ├── database.py             # DB Connection & session
│   │   ├── db_models.py            # SQLAlchemy ORM models
│   │   ├── dependency.py           # Dependency injection (Storage & DB)
│   │   ├── loader.py               # Model loader abstraction (Sklearn Joblib)
│   │   ├── observability.py        # Metrics, structured logging, and Request IDs
│   │   ├── repository.py           # Database operations
│   │   ├── schemas.py              # Pydantic data validation
│   │   ├── service.py              # Business logic
│   │   └── storage.py              # Artifact storage abstraction
│   └── utils/
│       └── logger.py               # Custom dynamic logging module
│
├── tests/                          # Testing directory
│   ├── test_health.py              # Health check tests
│   ├── test_loader.py              # Model loader and cache tests
│   ├── test_observability.py       # Metrics, logging, and tracing tests
│   ├── test_prediction.py          # End-to-end inference API tests
│   ├── test_registry.py            # Model registry integration tests
│   └── test_storage.py             # Storage abstraction unit tests
│
├── .pre-commit-config.yaml         # Enforces Ruff formatting before commits
├── Makefile                        # CLI orchestrator (make train, make serve)
├── pyproject.toml                  # Centralized config for Ruff, Pytest
└── requirements.txt                # Python dependencies

```

Cleaning Up
To remove the virtual environment and clean up your local workspace, simply run:

```bash
make clean

```
