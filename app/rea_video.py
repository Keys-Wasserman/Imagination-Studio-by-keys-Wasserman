"""Optional, local rea-video breakdowns through the Studio job queue."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from fastapi import HTTPException

EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm"}


def executable() -> Path:
    prefix = Path(os.environ.get("PREFIX") or Path.home() / ".local/opt/tensorfold-studio")
    return prefix / "rea-video-venv" / "bin" / "rea-video"


def status() -> dict:
    if os.name == "nt":
        return {"ready": False, "why": "The Studio's rea-video job is available on Mac and Linux; its Windows runtime has not been checked."}
    if not executable().is_file() or not os.access(executable(), os.X_OK) or not (executable().parent / "python").is_file():
        return {"ready": False, "why": "Install the optional analyzer with bash scripts/setup-rea-video.sh, then refresh Studio."}
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        return {"ready": False, "why": "rea-video needs ffmpeg and ffprobe on this machine."}
    return {"ready": True, "why": "", "source": "https://github.com/JuneYaooo/rea-video"}


def parameters(params: dict, inside) -> dict:
    if not isinstance(params, dict) or not isinstance(params.get("video"), str):
        raise HTTPException(400, "choose a video from this Studio's Library")
    path = inside(params["video"])
    if path.suffix.lower() not in EXTENSIONS or not path.is_file():
        raise HTTPException(400, "choose an existing mp4, mov, mkv or webm in this Studio")
    if path.stat().st_size > 2 * 1024**3:
        raise HTTPException(400, "the first breakdown route takes a video up to 2 GB")
    audio = params.get("audio", False)
    if not isinstance(audio, bool):
        raise HTTPException(400, "audio is true or false")
    return {"video": str(path), "audio": audio}


def build(params: dict, home: Path, job_id: str, inside) -> tuple[list[str], dict, list[str]]:
    state = status()
    if not state["ready"]:
        raise HTTPException(501, state["why"])
    chosen = parameters(params, inside)
    target = home / "analysis" / job_id
    output = [str(target.with_suffix(".md")), str(target.with_suffix(".zip"))]
    script = Path(__file__).resolve().parent.parent / "scripts" / "rea-video-job.py"
    command = [str(executable().parent / "python"), str(script), "--binary", str(executable()),
               "--video", chosen["video"], "--target", str(target)]
    if chosen["audio"]:
        command.append("--audio")
    return command, {}, output
