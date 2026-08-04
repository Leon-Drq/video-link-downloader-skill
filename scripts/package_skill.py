#!/usr/bin/env python3
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "dist" / "video-link-downloader.skill"


def main() -> int:
    subprocess.run(["python3", str(ROOT / "scripts" / "validate_skill.py")], check=True)
    with tempfile.TemporaryDirectory() as temp:
        package = Path(temp) / "video-link-downloader"
        (package / "scripts").mkdir(parents=True)
        shutil.copy2(ROOT / "SKILL.md", package / "SKILL.md")
        shutil.copy2(ROOT / "requirements.txt", package / "requirements.txt")
        shutil.copy2(ROOT / "scripts" / "video_dl.py", package / "scripts" / "video_dl.py")
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        archive = shutil.make_archive(str(OUTPUT.with_suffix("")), "zip", temp)
        Path(archive).replace(OUTPUT)
    print(f"Packaged: {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
