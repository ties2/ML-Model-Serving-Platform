# ML Model Serving Platform (MSP)

> Production-grade infrastructure for **registering, versioning, serving, and monitoring machine learning models** — built to demonstrate MLOps, ML-infrastructure, and backend engineering, not just another ML classifier.

![Python](https://img.shields.io/badge/Python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-async-009688)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED)
![Prometheus](https://img.shields.io/badge/Prometheus-metrics-E6522C)
![Tests](https://img.shields.io/badge/tests-pytest-green)
![Status](https://img.shields.io/badge/status-active%20development-yellow)

A real-time model-serving backend with a metadata **registry**, artifact **storage abstraction**, in-memory **model cache**, a full **prediction API**, safe **promotion / rollback** between lifecycle stages, and first-class **observability** (Prometheus metrics + structured JSON logs). The ML model itself is intentionally a small component — the engineering value is everything around it.

---

## Table of contents

1. [What this project is](#1-what-this-project-is)
2. [The mental model: model vs. platform](#2-the-mental-model-model-vs-platform)
3. [Architecture](#3-architecture)
4. [Tech stack](#4-tech-stack)
5. [Data model (Model Registry)](#5-data-model-model-registry)
6. [API reference](#6-api-reference)
7. [Design decisions & trade-offs](#7-design-decisions--trade-offs)
8. [Getting started](#8-getting-started)
9. [Testing](#9-testing)
10. [Observability](#10-observability)
11. [Current status](#11-current-status)
12. [Known limitations & design notes](#12-known-limitations--design-notes)
13. [Roadmap](#13-roadmap)
14. [Project structure](#14-project-structure)
15. [Author](#15-author)

---

## 1. What this project is

### The problem

In most ML projects a trained model file (`model.joblib`) is committed straight into a Git repo and loaded by whatever app happens to need it. That works for a demo, but it breaks in production:

- You cannot answer *"which model version is live right now?"*
- You cannot roll back a bad model without editing code and rebuilding.
- You have no record of *how* a model was produced or which one served a given request.
- Two models with different feature contracts silently collide.

### The goal

This platform is the **infrastructure that sits around a model** and answers those questions: a registry, versioning, an artifact store, a serving contract, a promotion/rollback workflow, and observability. The first use case is **real-time fraud-risk scoring**, but the platform is deliberately decoupled from any single algorithm — a `scikit-learn` model today can be swapped for `XGBoost` tomorrow behind the same API.

> **Design principle:** the serving infrastructure must not be tightly coupled to one specific ML algorithm.

---

## 2. The mental model: model vs. platform

Two distinct concepts live in this repo, and keeping them separate is the whole point.

**A) The ML model** — a pure function:

```
transaction features  ─►  scikit-learn model  ─►  prediction / score
```

**B) The serving platform** — the system this repo actually builds:

```
Client
  │  POST /models/{name}/versions/{version}/predict
  ▼
API (FastAPI)  ─►  Service (business rules)  ─►  Registry (PostgreSQL)
                          │
                          ├─► Artifact Storage (local://, path-traversal safe)
                          ├─► Model Loader (joblib → in-memory object)
                          ├─► Model Cache (hot models kept in RAM)
                          └─► Observability (Prometheus + structured logs)
```

This is **primarily (B)**. That is what makes it an MLOps / ML-infrastructure project rather than a data-science notebook.

---

## 3. Architecture

### Layered application architecture

Business logic never lives in a route handler. Every request flows through clean, testable layers:

```
        HTTP request
             │
             ▼
     ┌───────────────┐
     │   API layer   │   src/serving/api.py       routing, request/response shape
     └───────┬───────┘
             │
             ▼
     ┌───────────────┐
     │ Service layer │   src/serving/service.py   business rules, lifecycle, HTTP errors
     └───────┬───────┘
             │
   ┌─────────┼───────────────────────────┐
   ▼         ▼                            ▼
┌────────┐ ┌──────────────┐        ┌──────────────┐
│Repository│ │Storage/Loader│        │ Observability │
│(only SQL)│ │  + Cache     │        │ metrics/logs  │
└────┬─────┘ └──────────────┘        └──────────────┘
     ▼
┌───────────────┐
│  PostgreSQL   │   via SQLAlchemy ORM
└───────────────┘
```

- **API** — declares endpoints, validates I/O with Pydantic, injects a DB session. No SQL, no business logic.
- **Service** — enforces rules (unique model names, no duplicate versions, no serving archived models) and owns the promotion/rollback workflow.
- **Repository** — the single place that issues SQLAlchemy queries. Swappable without touching business logic.
- **Storage / Loader / Cache** — pluggable abstractions (`Protocol` interfaces) so a local disk backend can become S3, and joblib can become ONNX, without touching the API.

### Runtime topology

```
              ┌────────────────────────────────────────┐
              │              docker compose               │
   :8000 ───► │  api        (FastAPI / uvicorn)          │
              │    │  depends_on: db healthy              │
   :5432 ───► │  db         (PostgreSQL 15)              │
   :9090 ───► │  prometheus (scrapes api:8000/metrics)   │
   :3000 ───► │  grafana    (dashboards)                 │
              └────────────────────────────────────────┘
```

---

## 4. Tech stack

| Concern                | Technology                          | Status         |
| ---------------------- | ----------------------------------- | -------------- |
| API framework          | FastAPI + Uvicorn                   | ✅ Implemented |
| Validation / settings  | Pydantic v2, pydantic-settings      | ✅ Implemented |
| ORM                    | SQLAlchemy 2.x                      | ✅ Implemented |
| Database               | PostgreSQL 15                       | ✅ Implemented |
| ML runtime             | scikit-learn + joblib               | ✅ Implemented |
| Artifact storage       | Local backend (S3-ready abstraction)| ✅ Implemented |
| Model cache            | In-memory (Redis-ready abstraction) | ✅ Implemented |
| Observability          | prometheus-client, structured logs, ContextVar request IDs | ✅ Implemented |
| Metrics / dashboards   | Prometheus + Grafana                | ✅ Wired (compose + provisioning) |
| Containerization       | Docker, Docker Compose              | ✅ Implemented |
| Testing                | pytest, httpx (TestClient)          | ✅ Implemented |
| Experiment tracking    | MLflow                              | 🚧 Planned     |
| Data versioning        | DVC                                 | 🚧 Scaffolded  |
| CI/CD & pre-commit     | GitHub Actions, Ruff hooks          | 🚧 Scaffolded  |
| Drift detection        | Custom monitoring module            | 🚧 Planned     |
| Orchestration          | Kubernetes                          | 🚧 Planned     |

> Items marked 🚧 exist as **scaffolding** (placeholder files / commented dependencies) so the structure is ready but the feature is not yet implemented. This README states current reality first and roadmap second, on purpose.

---

## 5. Data model (Model Registry)

Two tables with a one-to-many relationship:

```
┌────────────────────────────┐          ┌──────────────────────────────────────┐
│ models                     │  1     N │ model_versions                        │
├────────────────────────────┤ ───────► ├──────────────────────────────────────┤
│ id           PK            │          │ id            PK                      │
│ name         UNIQUE, idx   │          │ model_id      FK → models.id          │
│ description  nullable      │          │ version                               │
│ created_at                 │          │ framework                             │
└────────────────────────────┘          │ model_format                          │
                                         │ artifact_uri                          │
   cascade: delete-orphan                │ status  (staging/production/archived) │
                                         │ created_at                            │
                                         │ UNIQUE(model_id, version)             │
                                         │ PARTIAL UNIQUE(model_id) WHERE        │
                                         │        status = 'production'          │
                                         └──────────────────────────────────────┘
```

Constraints enforced at the **database** level (not just in Python):

- `models.name` is unique.
- `(model_id, version)` is unique — a model can't register the same version twice.
- A **partial unique index** guarantees **at most one `production` version per model** — the database itself makes an invalid promotion impossible, even under concurrency.
- Deleting a model cascades to its versions (`delete-orphan`).

Lifecycle:

```
fraud-model
 ├── 1.0.0 → archived
 ├── 1.1.0 → production   ◄── exactly one, enforced by the DB
 └── 2.0.0 → staging
```

Promotion is **transactional**: promoting `2.0.0` archives the current production version and activates the new one in a single commit, rolling back entirely on any failure, and invalidating the old version from the cache.

---

## 6. API reference

Interactive Swagger UI is auto-generated at **`http://localhost:8000/docs`** when the app is running.

### Health & observability

| Method | Path       | Description                                   |
| ------ | ---------- | --------------------------------------------- |
| `GET`  | `/health`  | Liveness check → `{"status": "ok"}`           |
| `GET`  | `/metrics` | Prometheus-compatible metrics exposition      |

### Model registry

| Method | Path                             | Description                             |
| ------ | -------------------------------- | --------------------------------------- |
| `POST` | `/models`                        | Register a new model                    |
| `GET`  | `/models`                        | List all models                         |
| `GET`  | `/models/{model_name}`           | Get one model by name (404 if absent)   |
| `POST` | `/models/{model_name}/versions`  | Register a new version                   |
| `GET`  | `/models/{model_name}/versions`  | List versions of a model                 |

### Model management & lifecycle

| Method | Path                                                | Description                                        |
| ------ | --------------------------------------------------- | -------------------------------------------------- |
| `POST` | `/models/{model_name}/versions/{version}/load`      | Load an artifact into the in-memory cache          |
| `GET`  | `/models/{model_name}/versions/{version}/status`    | Is this version currently loaded in RAM?           |
| `POST` | `/models/{model_name}/versions/{version}/promote`   | Promote to production (auto-archives the previous) |
| `GET`  | `/models/{model_name}/production`                   | Get the current production version                 |

### Inference

| Method | Path                                                | Description                                          |
| ------ | --------------------------------------------------- | ---------------------------------------------------- |
| `POST` | `/models/{model_name}/versions/{version}/predict`   | Predict against a specific version (auto-loads)      |
| `POST` | `/models/{model_name}/predict`                      | Predict against the current production version       |

**Predict**

```http
POST /models/fraud-model/versions/1.0.0/predict
Content-Type: application/json
```
```json
{ "features": [0.2, 1.5, 10.0, 3.2] }
```

Response `200`:

```json
{ "model_name": "fraud-model", "version": "1.0.0", "prediction": 1 }
```

The prediction path is defensive: empty features → `422`, wrong feature count vs. the model's `n_features_in_` → `422`, archived version → `409`, missing artifact → `404`, corrupt artifact → `500` — each mapped to a specific status code and recorded as a labelled Prometheus error metric.

---

## 7. Design decisions & trade-offs

**Why a Model Registry instead of committing `model.joblib` to Git?**
Git is built for text, not large binaries — every retrain bloats history. A lone `.joblib` is a black box with no lineage. A registry stores metadata, supports lifecycle stages, and lets deployment pick the production model **without changing application code**. *Git manages code; a registry manages artifacts.*

**Why the three-layer (API → Service → Repository) split?**
Separation of concerns makes each layer independently testable and swappable — change the database without touching business rules, change routing without touching either.

**Why `Protocol`-based Storage / Loader / Cache abstractions?**
Each is an interface with one concrete implementation today (local disk, joblib, in-memory dict). The point is that swapping in S3, ONNX, or Redis is a new class, not a rewrite. The dependency-injection seam (`get_artifact_storage()`) is where that choice is made.

**Why separate `Create` and `Response` Pydantic schemas?**
`Create` schemas carry only what a client may send; `Response` schemas add server-generated fields (`id`, `created_at`) and use `from_attributes=True` to serialize straight from ORM objects. This keeps validation strict and avoids leaking internal fields.

**Why enforce "one production version" in the database?**
Application-level checks race under concurrency. A partial unique index makes the invariant a property of the data, not of the code path that happens to run.

**Trade-off accepted for now:** tables are created at startup via `Base.metadata.create_all()` rather than Alembic migrations — simple to run, but not how schema changes should be managed long-term (see limitations).

---

## 8. Getting started

### Prerequisites

- Docker & Docker Compose
- (Optional, to run outside containers) Python 3.12

### 1. Clone

```bash
git clone https://github.com/<your-username>/ML-Model-Serving-Platform.git
cd ML-Model-Serving-Platform
```

### 2. Configure environment

```bash
cp env.example .env
```

Key variables (`POSTGRES_HOST` is `db` inside Docker, `localhost` if you run uvicorn on the host):

```dotenv
POSTGRES_USER=admin
POSTGRES_PASSWORD=secretpassword
POSTGRES_DB=ml_serving_db
POSTGRES_HOST=db
POSTGRES_PORT=5432
APP_ENV=development
ARTIFACT_STORAGE_BACKEND=local
LOCAL_ARTIFACT_DIR=/app/model_artifacts/
```

### 3. Start the stack

```bash
docker compose up --build -d
```

This launches PostgreSQL, waits for it to be healthy, then starts the API on port 8000, plus Prometheus (`:9090`) and Grafana (`:3000`).

### 4. Verify

```bash
curl http://localhost:8000/health          # {"status":"ok"}
# Interactive docs:  http://localhost:8000/docs
# Metrics:           http://localhost:8000/metrics
# Prometheus targets: http://localhost:9090/targets
# Grafana:           http://localhost:3000
```

### 5. Generate demo traffic (optional)

```bash
docker compose exec api python generate_traffic.py
```

Registers a model, promotes it to production, and fires 100 predictions so the Grafana dashboard lights up.

### Run the API on the host (optional)

```bash
make                 # create .venv + install requirements
source .venv/bin/activate
uvicorn src.serving.app:app --host 0.0.0.0 --port 8000 --reload
# remember to set POSTGRES_HOST=localhost in .env
```

### Clean up

```bash
make clean               # remove the local virtualenv
docker compose down -v   # stop containers and drop volumes
```

---

## 9. Testing

Tests run **inside the container**, against a **real PostgreSQL** instance, for environment parity. 2 GB of shared memory is allocated to avoid `Bus error` crashes during joblib/NumPy work on some hosts.

```bash
docker compose run --rm --shm-size=2gb api pytest -v
```

Coverage spans 8 suites — storage, loader & cache, registry, prediction, lifecycle/promotion, observability, infrastructure, and health — including error paths, cache-hit behaviour (via mocking), path-traversal rejection, and transactional promotion.

> **Why Docker for tests?** `src/serving/app.py` triggers `Base.metadata.create_all()` on import, so the test process needs a reachable database. Running through Compose guarantees one is present.

---

## 10. Observability

Every prediction and lifecycle event is instrumented. Metrics are exposed at `/metrics` and scraped by Prometheus; a provisioned Grafana dashboard visualizes them.

| Metric                          | Type      | Labels                       |
| ------------------------------- | --------- | ---------------------------- |
| `prediction_requests_total`     | Counter   | model, version, status       |
| `prediction_errors_total`       | Counter   | model, version, error_type   |
| `prediction_latency_seconds`    | Histogram | model, version               |
| `model_load_total`              | Counter   | model, version, status       |
| `model_load_latency_seconds`    | Histogram | model, version               |
| `model_cache_hits_total`        | Counter   | model, version               |
| `model_cache_misses_total`      | Counter   | model, version               |
| `model_promotions_total`        | Counter   | model, version, status       |

Logs are emitted as **structured JSON** with a per-request ID propagated through a `ContextVar` (set by middleware from an inbound `X-Request-ID` header or generated), so a single request can be traced across layers without threading the ID through every function signature. Logs deliberately carry no feature values (no PII).

---

## 11. Current status

Delivered ticket-by-ticket (MSP-001 → MSP-008), mirroring a real team.

| Ticket    | Title                                        | Status  |
| --------- | -------------------------------------------- | ------- |
| MSP-001   | Bootstrap serving platform (FastAPI + Docker)| ✅ Done |
| MSP-002   | Model registry (PostgreSQL metadata)         | ✅ Done |
| MSP-003   | Artifact storage abstraction                 | ✅ Done |
| MSP-004   | Model loader & in-memory cache               | ✅ Done |
| MSP-005   | Prediction API (real-time inference)         | ✅ Done |
| MSP-006   | Observability (metrics, logs, request IDs)   | ✅ Done |
| MSP-008   | Lifecycle: transactional promotion & rollback| ✅ Done |

**Scaffolding present, not yet implemented:** MLflow training pipeline, DVC data versioning, drift detection, GitHub Actions CI/CD, and Ruff pre-commit hooks. See the roadmap.

---

## 12. Known limitations & design notes

Honest engineering notes — intentional simplifications for the current stage, each mapping to a future ticket.

- **No schema migrations.** Tables are created with `create_all()` at startup. Production should adopt **Alembic** for versioned, reversible schema changes.
- **In-process cache only.** The cache is a per-process dict, so it does not survive restarts and is not shared across replicas. The `ModelCache` interface is Redis-ready for the multi-replica case.
- **Local storage backend only.** The `ArtifactStorage` interface is designed for S3/GCS; only the local backend is implemented today.
- **`status` is free text.** `staging` / `production` / `archived` are conventions; a DB `Enum` or `CHECK` constraint would harden them.
- **POST returns `200`, not `201 Created`.** Functionally fine; a small REST-conventions polish.
- **No auth, rate limiting, or pagination yet.** Explicitly scheduled on the roadmap.

---

## 13. Roadmap

**Phase 1 — Backend foundation** ✅ registry, storage, loader/cache, prediction, observability, lifecycle.

**Phase 2 — Production hardening** 🚧 Redis-backed distributed cache · JWT auth + rate limiting · pagination · Alembic migrations · `201 Created` semantics.

**Phase 3 — Kubernetes & scale** 🚧 multi-stage build · Deployment/Service/ConfigMap/Secret · horizontal scaling · liveness/readiness probes · Locust load tests capturing p50/p95/p99.

**Phase 4 — Full MLOps** 🚧 MLflow experiment tracking · DVC data versioning · canary & A/B deployment · automatic rollback on error-rate/latency regression · drift detection · GitHub Actions CI/CD (lint → test → build → deploy) with Ruff pre-commit hooks.

**Portfolio arc** — this is Project 2 of a planned three-project MLOps portfolio:

```
ML Application         ML Infrastructure          Security ML
(Fraud Detection)  ─►  (this: Model Serving)  ─►  (AI Security Detection)
```

The next project reuses this platform's serving infrastructure for inference.

---

## 14. Project structure

```text
ML-Model-Serving-Platform/
│
├── src/
│   ├── serving/                     # the serving platform itself
│   │   ├── app.py                   # FastAPI entrypoint, middleware, /health, /metrics
│   │   ├── api.py                   # routes (registry, load, predict, promote)
│   │   ├── service.py               # business logic + lifecycle workflow
│   │   ├── repository.py            # DB access layer (queries only)
│   │   ├── db_models.py             # ORM tables: DBModel, DBModelVersion
│   │   ├── schemas.py               # Pydantic request/response models
│   │   ├── database.py              # SQLAlchemy engine, session, get_db()
│   │   ├── config.py                # settings from environment (.env)
│   │   ├── storage.py               # artifact storage abstraction (local://)
│   │   ├── loader.py                # sklearn/joblib model loader
│   │   ├── cache.py                 # in-memory model cache
│   │   ├── observability.py         # metrics, structured logs, request IDs
│   │   └── dependency.py            # DI for storage backend
│   │
│   ├── models/                      # ML domain (scaffolding)
│   │   ├── train.py                 # (planned) MLflow training pipeline
│   │   └── evaluate.py              # (planned) offline evaluation
│   ├── monitoring/
│   │   └── drift_detector.py        # (planned) data/concept drift
│   └── utils/
│       └── logger.py                # (planned) shared logging helper
│
├── tests/                           # 8 pytest suites (run in Docker)
├── monitoring/
│   ├── prometheus/prometheus.yml    # scrape config
│   └── grafana/                     # provisioned datasource + dashboard
├── deployment/Dockerfile            # python:3.12-slim + healthcheck
├── docker-compose.yml               # api · db · prometheus · grafana
├── generate_traffic.py              # demo traffic generator
├── requirements.txt
├── Makefile                         # venv bootstrap / cleanup
├── pyproject.toml                   # pytest + tooling config
├── env.example                      # environment variable template
├── .github/workflows/ci-cd.yaml     # (planned) CI/CD
├── .pre-commit-config.yaml          # (planned) Ruff hooks
└── data/*.dvc                       # (planned) DVC-tracked data
```

---

## 15. Author

**Nirvana Fanaelahi**

Built as a hands-on MLOps / ML-infrastructure portfolio project. The emphasis is deliberately on **production engineering around a model** — versioning, serving, safe promotion, and observability — rather than on the model itself.

---

*This README reflects the actual state of the codebase. Features labelled "planned" / 🚧 are scaffolded but not yet implemented, and are tracked in the roadmap.*