import json
from datetime import datetime, timezone
from pathlib import Path

from python_services.storage.manifests import SegmentRecord, SessionExport
from python_services.storage.persistence import list_exports, load_export, prune_exports, save_export
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


def test_prune_exports_removes_old_files(tmp_path):
    recent = SessionExport(
        session_id="recent",
        created_at=datetime(2024, 1, 10, tzinfo=timezone.utc),
        language="fa",
        segments=[SegmentRecord(speaker="spk", text="hi", speaker_label=None)],
        summary=Summary(highlight="now", bullet_points=["bp"]),
    )
    old = SessionExport(
        session_id="old",
        created_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
        language="fa",
        segments=[SegmentRecord(speaker="spk2", text="bye", speaker_label=None)],
        summary=Summary(highlight="then", bullet_points=["bp"]),
    )

    save_export(recent, base_dir=str(tmp_path))
    save_export(old, base_dir=str(tmp_path))

    removed = prune_exports(base_dir=str(tmp_path), max_age_days=365, now=datetime(2024, 1, 15, tzinfo=timezone.utc))

    assert removed == ["old"]
    assert (Path(tmp_path) / "exports" / "recent.json").exists()
    assert not (Path(tmp_path) / "exports" / "old.json").exists()
