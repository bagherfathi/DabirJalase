from pathlib import Path

from python_services.scripts.demo_session import run_demo_session


def test_demo_session_produces_labeled_manifest(tmp_path: Path):
    manifest, saved_path = run_demo_session(storage_dir=tmp_path)

    assert manifest.session_id == "demo-session"
    assert manifest.segments, "segments should be populated"
    assert all(segment.speaker_label for segment in manifest.segments)
    assert manifest.summary.bullet_points
    assert saved_path is not None
    assert saved_path.exists()

    # ensure persisted manifest includes expected session id
    assert saved_path.stem == manifest.session_id
