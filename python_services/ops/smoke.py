"""Lightweight smoke test harness for the Python services scaffold.

Runs an end-to-end flow against the in-process FastAPI app to validate that
core session and export behaviors are still healthy without requiring real
model downloads or an external server process.
"""
from __future__ import annotations

import importlib
import json
import os
import tempfile
from contextlib import contextmanager
from typing import Dict, Tuple
from unittest.mock import patch

from fastapi import TestClient


@contextmanager
def _patched_env(storage_dir: str | None, api_key: str | None):
    env_updates: Dict[str, str] = {}
    if storage_dir:
        env_updates["PY_SERVICES_STORAGE_DIR"] = storage_dir
    if api_key:
        env_updates["PY_SERVICES_API_KEY"] = api_key
    else:
        env_updates["PY_SERVICES_API_KEY"] = ""

    # Keep retention flexible for CI; disable pruning by default for visibility.
    env_updates.setdefault("PY_SERVICES_EXPORT_RETENTION_DAYS", "none")

    with patch.dict(os.environ, env_updates, clear=False):
        yield


def _load_server():
    # Reload to ensure settings reflect patched environment variables.
    return importlib.reload(importlib.import_module("python_services.api.server"))


def run_smoke(storage_dir: str | None = None, api_key: str | None = None) -> Tuple[str, Dict[str, object]]:
    """Execute an in-process smoke test and return a human-friendly summary.

    The flow exercises session creation, append + diarization, speaker labeling,
    summary generation, export + persistence, and retrieval.
    """

    with tempfile.TemporaryDirectory() as default_dir, _patched_env(storage_dir or default_dir, api_key):
        server = _load_server()
        client = TestClient(server.app)

        headers = {}
        if api_key:
            headers["x-api-key"] = api_key

        session_id = "smoke-session"
        transcript_body = "Ali: salam, khobi? Sara: man khubam."  # deterministic stub input

        created = client.post("/sessions", headers=headers, json={"session_id": session_id, "language": "fa"})
        appended = client.post(
            "/sessions/append",
            headers=headers,
            json={"session_id": session_id, "transcript": transcript_body},
        )

        speaker_id = appended.json()["new_speakers"][0]
        labeled = client.post(
            f"/sessions/{session_id}/speakers",
            headers=headers,
            json={"speaker_id": speaker_id, "display_name": "Ali"},
        )

        summary = client.get(f"/sessions/{session_id}/summary", headers=headers)
        export = client.get(f"/sessions/{session_id}/export", headers=headers)
        stored = client.post(f"/sessions/{session_id}/export/store", headers=headers)
        listed = client.get("/exports", headers=headers)
        fetched = client.get(f"/exports/{session_id}", headers=headers)

        manifest = fetched.json()

        report = {
            "session": created.json(),
            "segments": labeled.json()["segments"],
            "summary": summary.json(),
            "export": export.json(),
            "storage_path": stored.json()["saved_path"],
            "exports": listed.json()["exports"],
            "fetched": manifest,
        }

        return "ok", report


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Run an in-process smoke test against the scaffold API")
    parser.add_argument("--api-key", dest="api_key", default=None, help="API key to include on requests if enforcement is on")
    parser.add_argument("--storage-dir", dest="storage_dir", default=None, help="Directory to persist smoke test exports")

    args = parser.parse_args()
    status, report = run_smoke(storage_dir=args.storage_dir, api_key=args.api_key)
    print(json.dumps({"status": status, "report": report}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
