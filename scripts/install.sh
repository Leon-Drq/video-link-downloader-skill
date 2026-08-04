#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CODEX_BASE="${CODEX_HOME:-$HOME/.codex}"
SKILL_DIR="$CODEX_BASE/skills/video-link-downloader"
VENV_DIR="$SKILL_DIR/.venv"
BIN_DIR="$HOME/.local/bin"

python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/python" -m pip install -r "$PROJECT_DIR/requirements.txt"

mkdir -p "$SKILL_DIR/scripts" "$BIN_DIR"
cp "$PROJECT_DIR/SKILL.md" "$SKILL_DIR/SKILL.md"
cp "$PROJECT_DIR/requirements.txt" "$SKILL_DIR/requirements.txt"
cp "$PROJECT_DIR/scripts/video_dl.py" "$SKILL_DIR/scripts/video_dl.py"
chmod +x "$SKILL_DIR/scripts/video_dl.py"

cat > "$BIN_DIR/video-dl" <<EOF
#!/usr/bin/env bash
exec "$VENV_DIR/bin/python" "$SKILL_DIR/scripts/video_dl.py" "\$@"
EOF
chmod +x "$BIN_DIR/video-dl"

echo "Installed Skill: $SKILL_DIR"
echo "Installed CLI:   $BIN_DIR/video-dl"
echo "If needed, add $BIN_DIR to PATH."

