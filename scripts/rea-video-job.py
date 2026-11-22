#!/usr/bin/env python3
"""Run one offline rea-video breakdown and keep its outputs in Studio's Library."""

import argparse
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", required=True)
    parser.add_argument("--video", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--audio", action="store_true")
    args = parser.parse_args()
    target = Path(args.target)
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=target.name + "-", dir=target.parent) as folder:
        work = Path(folder)
        command = [args.binary, "decompose", args.video, "-o", str(work), "--lang", "en", "--no-vlm", "--workers", "1"]
        if not args.audio:
            command.extend(("--no-stems", "--no-asr", "--no-speakers"))
        subprocess.run(command, check=True, timeout=3600)
        report, card = work / "report.html", work / "VIDEO.md"
        if not report.is_file() or not card.is_file():
            raise RuntimeError("rea-video finished without report.html and VIDEO.md")
        archive = target.with_suffix(".zip")
        with zipfile.ZipFile(archive.with_suffix(".zip.part"), "w", zipfile.ZIP_DEFLATED) as package:
            for path in sorted(work.rglob("*")):
                if path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(work.resolve()):
                    package.write(path, path.relative_to(work))
        archive.with_suffix(".zip.part").replace(archive)
        shutil.copyfile(card, target.with_suffix(".md"))
    print("[studio] Breakdown: " + str(target.with_suffix(".md")), flush=True)


if __name__ == "__main__":
    main()
