import json
from datetime import datetime, timezone
from pathlib import Path

from python_services.storage.manifests import SegmentRecord, SessionExport
from python_services.storage.persistence import list_exports, load_export, save_export
from python_services.summarization.summarizer import Summary


def test_save_and_load_export_round_trip(tmp_path):
    export = SessionExport(
        session_id="persist-me",
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        language="fa",
        segments=[SegmentRecord(speaker="spk1", text="salam", speaker_label="Host")],
        summary=Summary(highlight="hello", bullet_points=["point"]),
    )

    saved = save_export(export, base_dir=str(tmp_path))
    assert saved.exists()

    loaded = load_export("persist-me", base_dir=str(tmp_path))

    assert loaded.session_id == export.session_id
    assert loaded.created_at == export.created_at
    assert loaded.language == export.language
    assert loaded.segments[0].speaker_label == "Host"
    assert loaded.summary.highlight == "hello"


def test_list_exports_returns_sorted_ids(tmp_path):
    export_dir = Path(tmp_path) / "exports"
    export_dir.mkdir()
    for name in ["b.json", "a.json", "c.json"]:
        (export_dir / name).write_text(json.dumps({"summary": {"highlight": "h", "bullet_points": []}}))

    result = list_exports(base_dir=str(tmp_path))

    assert result == ["a", "b", "c"]
