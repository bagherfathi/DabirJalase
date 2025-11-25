"""HTTP demo using the MeetingAssistantClient to exercise the scaffold.

Run a local server first (e.g. ``python -m python_services``) then execute:

    python -m python_services.scripts.http_client_demo

Environment variables:
    SERVICE_BASE_URL: target base URL (default: http://localhost:8000)
    SERVICE_API_KEY: optional API key to include with requests
"""
from __future__ import annotations

import os
import textwrap

from python_services.client import MeetingAssistantClient


def main() -> None:
    base_url = os.getenv("SERVICE_BASE_URL", "http://localhost:8000")
    api_key = os.getenv("SERVICE_API_KEY")
    client = MeetingAssistantClient(base_url, api_key=api_key)

    session = client.create_session(title="HTTP demo", agenda=["demo", "wrap-up"])
    session_id = session["session_id"]
    print(f"Created session: {session_id}")

    client.append_transcript(session_id, "سلام، این یک آزمایش است")
    client.append_transcript(session_id, "We are validating the HTTP client demo")

    summary = client.get_summary(session_id)
    print("Summary highlight:", summary["highlight"])

    stored = client.store_export(session_id)
    print("Stored export at:", stored["saved_path"])

    download = client.download_export(session_id, format="markdown")
    print("\nRendered export (markdown):\n")
    print(textwrap.indent(download, prefix="  "))


if __name__ == "__main__":
    main()
