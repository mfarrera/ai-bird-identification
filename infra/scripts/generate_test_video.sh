#!/usr/bin/env bash
set -euo pipefail

# Genera un vídeo sintètic amb un objecte movent-se, per validar el pipeline
# de moviment -> YOLO -> crop -> API -> BBDD sense material real d'ocells.
# YOLO NO reconeixerà la forma com a "bird" (és sintètica) — només serveix
# per comprovar el flux fins la classificació.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
OUTPUT="$REPO_ROOT/apps/edge/media/sample.mp4"

mkdir -p "$(dirname "$OUTPUT")"
echo "Generant vídeo sintètic a $OUTPUT ..."

ffmpeg -y \
  -f lavfi -i "color=size=1280x720:rate=30:color=black:duration=30" \
  -vf "drawbox=x='mod(t*150\,1280-120)':y=300:w=120:h=120:color=white:t=fill" \
  -c:v libx264 -pix_fmt yuv420p \
  "$OUTPUT"

echo "Fet."
