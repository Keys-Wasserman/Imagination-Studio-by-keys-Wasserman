"""The optional analyzer stays in the queue and produces a portable report package."""

import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import pytest
from fastapi import HTTPException

ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("STUDIO_HOME", str(Path(tempfile.mkdtemp()) / "Studio"))
sys.path.insert(0, str(ROOT / "app"))
import rea_video  # noqa: E402
import server  # noqa: E402


def test_build_requires_local_media_and_uses_an_isolated_cli(tmp_path, monkeypatch):
    source = tmp_path / "clip with spaces.mp4"
    source.write_bytes(b"video")
    tool = tmp_path / "rea-video-venv/bin/rea-video"
    tool.parent.mkdir(parents=True)
    tool.write_text("")
    monkeypatch.setattr(rea_video, "status", lambda: {"ready": True, "why": ""})
    monkeypatch.setattr(rea_video, "executable", lambda: tool)
    command, env, outputs = rea_video.build({"video": str(source), "audio": True}, tmp_path, "job1", Path)
    assert command[0] == str(tool.parent / "python") and command[-1] == "--audio"
    assert command[command.index("--video") + 1] == str(source)
    assert env == {} and outputs == [str(tmp_path / "analysis/job1.md"), str(tmp_path / "analysis/job1.zip")]
    with pytest.raises(HTTPException, match="mp4, mov, mkv or webm"):
        rea_video.parameters({"video": str(tmp_path / "missing.mp4")}, Path)
    with pytest.raises(HTTPException, match="true or false"):
        rea_video.parameters({"video": str(source), "audio": "yes"}, Path)


def test_wrapper_keeps_the_report_and_shot_assets(tmp_path):
    source = tmp_path / "input.mp4"
    source.write_bytes(b"video")
    binary = tmp_path / "fake-rea-video"
    binary.write_text("#!/usr/bin/env python3\nimport pathlib, sys\n"
                      "assert '--no-vlm' in sys.argv and '--no-stems' in sys.argv and '--workers' in sys.argv\n"
                      "out = pathlib.Path(sys.argv[sys.argv.index('-o') + 1])\n"
                      "(out / 'shots').mkdir(parents=True)\n"
                      "(out / 'VIDEO.md').write_text('# Shot map\\n')\n"
                      "(out / 'report.html').write_text('<h1>Report</h1>')\n"
                      "(out / 'shots' / 'first.jpg').write_bytes(b'frame')\n")
    binary.chmod(0o755)
    target = tmp_path / "analysis" / "job1"
    subprocess.run([sys.executable, str(ROOT / "scripts/rea-video-job.py"), "--binary", str(binary),
                    "--video", str(source), "--target", str(target)], check=True, timeout=10, capture_output=True)
    assert target.with_suffix(".md").read_text() == "# Shot map\n"
    with zipfile.ZipFile(target.with_suffix(".zip")) as archive:
        assert set(archive.namelist()) == {"VIDEO.md", "report.html", "shots/first.jpg"}


def test_api_job_uses_studio_queue_and_refuses_outside_files(tmp_path, monkeypatch):
    home = tmp_path / "Studio"
    source = home / "uploads" / "clip.mp4"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"video")
    monkeypatch.setattr(server, "HOME", home)
    monkeypatch.setattr(rea_video, "status", lambda: {"ready": True, "why": ""})
    monkeypatch.setattr(rea_video, "executable", lambda: tmp_path / "venv/bin/rea-video")
    captured = []
    monkeypatch.setattr(server, "enqueue", lambda kind, title, params: captured.append((kind, title, params)) or {"id": "j1"})
    reply = server.queue_job({"kind": "rea_video", "params": {"video": "uploads/clip.mp4"}})
    assert reply == {"id": "j1"} and captured[0][0] == "rea_video"
    assert captured[0][2]["video"] == str(source) and captured[0][2]["audio"] is False
    outside = tmp_path / "outside.mp4"
    outside.write_bytes(b"video")
    with pytest.raises(HTTPException) as exc:
        server.queue_job({"kind": "rea_video", "params": {"video": str(outside)}})
    assert "outside the studio folder" in exc.value.detail
