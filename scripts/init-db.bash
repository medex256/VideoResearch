#!/usr/bin/env bash
set -e

echo "[INIT] Applying database migrations…"
flask db upgrade

if [ "${RUN_DB_INIT}" = "true" ]; then
  echo "[INIT] Performing full DB seed…"

  # 1) load videos & add info‐video (load_videos.py calls add_info_video() at the bottom)
  echo "  • Loading videos + info video"
  python load_videos.py

  # 2) translate category names
  echo "  • Translating categories"
  python translate_categories.py

  # 3) apply update/replace logic
  echo "  • Running update_video.py"
  python update_video.py

  echo "[INIT] Full DB seed complete."
else
  echo "[INIT] Skipping full seed (RUN_DB_INIT != true)"
fi