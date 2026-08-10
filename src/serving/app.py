from fastapi import FastAPI

app = FastAPI(title="MLOps Serving API")

@app.get("/health")
def health_check():
    return {"status": "ok"}

