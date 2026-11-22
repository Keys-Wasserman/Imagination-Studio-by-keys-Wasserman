#!/usr/bin/env bash
# Optional CPU video analysis, isolated from Studio's model and CUDA environments.
set -euo pipefail
PREFIX="${PREFIX:-$HOME/.local/opt/tensorfold-studio}"
VENV="$PREFIX/rea-video-venv"
REV="90eae960d13643e24a0066d6f569df7f390f0567"
command -v uv >/dev/null || { echo "uv is needed (the Studio one-shot installs it)" >&2; exit 2; }
command -v ffmpeg >/dev/null || { echo "ffmpeg is needed" >&2; exit 2; }
command -v ffprobe >/dev/null || { echo "ffprobe is needed" >&2; exit 2; }
REA_PYTHON="${REA_VIDEO_PYTHON:-$PREFIX/venv/bin/python}"
if [ ! -x "$REA_PYTHON" ]; then REA_PYTHON=python3; fi
uv venv --python "$REA_PYTHON" "$VENV"
uv pip install --python "$VENV/bin/python" "rea-video @ git+https://github.com/JuneYaooo/rea-video.git@$REV"
"$VENV/bin/rea-video" --help >/dev/null
echo "rea-video is ready for Studio. Its first audio separation may download about 216 MB of models."
