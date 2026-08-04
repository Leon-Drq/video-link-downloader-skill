#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "SKILL.md"


def main() -> int:
    text = SKILL.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        raise SystemExit("SKILL.md: missing YAML frontmatter")
    frontmatter = match.group(1)
    keys = re.findall(r"^([a-zA-Z0-9_-]+):", frontmatter, re.MULTILINE)
    if keys != ["name", "description"]:
        raise SystemExit(f"SKILL.md: expected name and description only, got {keys}")
    if "name: video-link-downloader" not in frontmatter:
        raise SystemExit("SKILL.md: invalid skill name")
    if len(text.splitlines()) >= 500:
        raise SystemExit("SKILL.md: must stay below 500 lines")
    script = ROOT / "scripts" / "video_dl.py"
    if not script.is_file():
        raise SystemExit("scripts/video_dl.py: missing")
    print("Skill validation: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

