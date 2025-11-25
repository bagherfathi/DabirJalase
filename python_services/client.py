"""Lightweight HTTP client for the meeting assistant service scaffold.

The client keeps dependencies minimal by defaulting to the standard library
for HTTP requests, while allowing a drop-in HTTP client (such as the built-in
`fastapi.TestClient`) to be supplied for in-process testing. This provides an
easy way for the desktop shell or other integrations to exercise the scaffold
without reimplementing request plumbing.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional


class ServiceError(RuntimeError):
    """Raised when the service returns a non-success response."""


@dataclass
class _Response:
    status_code: int
    text: str

    def json(self) -> Any:
        if not self.text:
            return {}
        return json.loads(self.text)


class _UrllibClient:
    """Simple HTTP client backed by urllib to avoid third-party deps."""

    def request(self, method: str, url: str, *, headers: Dict[str, str] | None = None, json_body: Any = None, params: Dict[str, Any] | None = None) -> _Response:
        headers = headers or {}
        if json_body is not None:
            headers["content-type"] = "application/json"
            data = json.dumps(json_body).encode("utf-8")
        else:
            data = None

        if params:
            query = urllib.parse.urlencode(params, doseq=True)
            url = f"{url}?{query}"

        req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
        try:
            with urllib.request.urlopen(req) as resp:
                body = resp.read().decode("utf-8")
                return _Response(status_code=resp.getcode(), text=body)
        except urllib.error.HTTPError as exc:  # pragma: no cover - exercised via client tests
            body = exc.read().decode("utf-8")
            return _Response(status_code=exc.code, text=body)


class MeetingAssistantClient:
    """Convenience wrapper over the REST scaffold.

    Usage:
        client = MeetingAssistantClient("http://localhost:8000", api_key="secret")
        session = client.create_session(title="Weekly Sync")
        client.append_transcript(session["session_id"], "Hello team")
        summary = client.get_summary(session["session_id"])
    """

    def __init__(self, base_url: str, api_key: str | None = None, http_client: Any | None = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.http = http_client or _UrllibClient()

    # Public API helpers -------------------------------------------------
    def health(self) -> Dict[str, Any]:
        return self._get("/health")

    def create_session(self, session_id: str | None = None, *, language: str = "fa", title: str | None = None, agenda: Optional[Iterable[str]] = None) -> Dict[str, Any]:
        payload = {
            "session_id": session_id or str(uuid.uuid4()),
            "language": language,
            "title": title,
            "agenda": list(agenda) if agenda is not None else None,
        }
        return self._post("/sessions", payload)

    def append_transcript(self, session_id: str, transcript: str) -> Dict[str, Any]:
        payload = {"session_id": session_id, "transcript": transcript}
        return self._post("/sessions/append", payload)

    def ingest_audio(self, session_id: str, samples: Iterable[int], *, threshold: int = 50, min_run: int = 3, transcript_hint: str = "speech detected") -> Dict[str, Any]:
        payload = {
            "transcript_hint": transcript_hint,
            "samples": list(samples),
            "threshold": threshold,
            "min_run": min_run,
        }
        return self._post(f"/sessions/{session_id}/ingest", payload)

    def set_metadata(self, session_id: str, *, title: str | None = None, agenda: Optional[Iterable[str]] = None) -> Dict[str, Any]:
        payload = {"title": title, "agenda": list(agenda) if agenda is not None else None}
        return self._patch(f"/sessions/{session_id}/metadata", payload)

    def get_session(self, session_id: str) -> Dict[str, Any]:
        return self._get(f"/sessions/{session_id}")

    def get_summary(self, session_id: str) -> Dict[str, Any]:
        return self._get(f"/sessions/{session_id}/summary")

    def export_session(self, session_id: str) -> Dict[str, Any]:
        return self._get(f"/sessions/{session_id}/export")

    def store_export(self, session_id: str) -> Dict[str, Any]:
        return self._post(f"/sessions/{session_id}/export/store", {})

    def list_exports(self) -> Dict[str, Any]:
        return self._get("/exports")

    def fetch_export(self, session_id: str) -> Dict[str, Any]:
        return self._get(f"/exports/{session_id}")

    def download_export(self, session_id: str, format: str = "markdown") -> str:
        response = self._request("GET", f"/exports/{session_id}/download", params={"format": format})
        return response.text

    def restore_export(self, session_id: str) -> Dict[str, Any]:
        return self._post(f"/exports/{session_id}/restore", {})

    def forget_speaker(self, session_id: str, speaker_id: str) -> Dict[str, Any]:
        payload = {"session_id": session_id, "speaker_id": speaker_id}
        return self._post(f"/sessions/{session_id}/speakers/forget", payload)

    def delete_session(self, session_id: str) -> Dict[str, Any]:
        return self._delete(f"/sessions/{session_id}")

    # Internal helpers ---------------------------------------------------
    def _headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {}
        if self.api_key:
            headers["x-api-key"] = self.api_key
        return headers

    def _with_params(self, url: str, params: Dict[str, Any] | None) -> str:
        if not params:
            return url
        query = urllib.parse.urlencode(params, doseq=True)
        return f"{url}?{query}"

    def _request(self, method: str, path: str, *, json_body: Any | None = None, params: Dict[str, Any] | None = None) -> _Response:
        url = f"{self.base_url}{path}"
        headers = self._headers()
        try:
            response = self.http.request(method, url, headers=headers, json_body=json_body, params=params)
        except TypeError:
            # Allow drop-in HTTP clients like requests or fastapi.TestClient that expect a ``json`` kwarg.
            url_with_params = self._with_params(url, params)
            kwargs = {"headers": headers}
            if json_body is not None:
                kwargs["json"] = json_body
            response = self.http.request(method, url_with_params, **kwargs)

        status = getattr(response, "status_code", 0)
        raw_text = getattr(response, "text", None)
        if raw_text is None:
            content = getattr(response, "content", "")
            if isinstance(content, bytes):
                raw_text = content.decode("utf-8")
            elif isinstance(content, str):
                raw_text = content
            else:
                raw_text = json.dumps(content)

        normalized = _Response(status_code=status, text=raw_text)
        if normalized.status_code >= 400:
            raise ServiceError(f"request failed ({normalized.status_code}): {normalized.text}")
        return normalized

    def _get(self, path: str, *, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
        return self._request("GET", path, params=params).json()

    def _post(self, path: str, json_body: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", path, json_body=json_body).json()

    def _patch(self, path: str, json_body: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("PATCH", path, json_body=json_body).json()

    def _delete(self, path: str) -> Dict[str, Any]:
        return self._request("DELETE", path).json()
