"""Support bundle utilities for the scaffold.

The bundle intentionally captures only deterministic, non-sensitive state so
the scaffold can be debugged offline without pulling production dependencies
or secrets. Real implementations can swap in richer diagnostics while keeping
the same API surface.
"""

from __future__ import annotations

import io
import json
import zipfile
from dataclasses import asdict
from datetime import datetime, timezone

from python_services.config import ServiceSettings
from python_services.ops.metrics import MetricsRegistry
from python_services.sessions import SessionStore
from python_services.storage import persistence


def _serialize_settings(settings: ServiceSettings) -> dict:
    data = asdict(settings)
    data["export_retention_days"] = settings.export_retention_days
    data["max_requests_per_minute"] = settings.max_requests_per_minute
    return data


def _serialize_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _serialize_exports(storage_dir: str, include_exports: bool) -> dict:
    export_ids = persistence.list_exports(storage_dir)
    exports: dict[str, object] = {"export_ids": export_ids}

    if not include_exports:
        return exports

    for export_id in export_ids:
        try:
            export = persistence.load_export(export_id, storage_dir)
        except FileNotFoundError:
            continue

        exports[export_id] = asdict(export)
        exports[export_id]["created_at"] = export.created_at.isoformat()

    return exports


def build_support_bundle(
    *,
    settings: ServiceSettings,
    metrics: MetricsRegistry,
    sessions: SessionStore,
    include_exports: bool = True,
) -> bytes:
    """Return a ZIP payload containing deterministic diagnostics."""

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("timestamp.txt", _serialize_timestamp())
        archive.writestr("settings.json", json.dumps(_serialize_settings(settings), indent=2, sort_keys=True))
        archive.writestr(
            "metrics.json",
            json.dumps({"counters": metrics.snapshot()}, indent=2, sort_keys=True),
        )
        archive.writestr(
            "sessions.json",
            json.dumps({"active_sessions": sessions.session_ids()}, indent=2, sort_keys=True),
        )

        exports = _serialize_exports(settings.storage_dir, include_exports)
        archive.writestr("exports/index.json", json.dumps(exports, indent=2, sort_keys=True))

    buffer.seek(0)
    return buffer.getvalue()
