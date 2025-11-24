"""Placeholder FastAPI/gRPC server wiring.
Extend with authenticated endpoints and streaming RPCs defined in the architecture blueprint.
"""

from fastapi import FastAPI

app = FastAPI(title="Meeting Assistant Services")


@app.get("/health")
def healthcheck():
    return {"status": "ok", "message": "scaffold"}
