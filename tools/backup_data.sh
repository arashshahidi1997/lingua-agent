#!/usr/bin/env bash
# Nightly backup of the app's data (.lingua-agent) to Google Drive with rclone.
#
#   tools/backup_data.sh            # run by ~/.config/systemd/user/lingua-backup.timer
#
# current/  mirrors the data dir; every file changed or deleted since the last run is kept under
# old/<date>/ for KEEP_DAYS, so a mistake on the laptop never wipes the backup. Skipped: the Piper voice
# model and the speech cache (re-downloadable / re-generated).
set -euo pipefail

SRC="${LINGUA_DATA_DIR:-$(cd "$(dirname "$0")/.." && pwd)/.lingua-agent}"
DEST="${LINGUA_BACKUP_DEST:-gdrive:home/language/lingua-agent-backup}"
KEEP_DAYS="${LINGUA_BACKUP_KEEP_DAYS:-60}"
STAMP="$(date +%Y-%m-%d_%H%M)"

[ -d "$SRC" ] || { echo "no data dir: $SRC" >&2; exit 1; }

rclone sync "$SRC" "$DEST/current" \
  --backup-dir "$DEST/old/$STAMP" \
  --exclude "voices/**" --exclude "tts_cache/**" --exclude "*.tmp" --exclude ".tmp-*" \
  --fast-list --transfers 4 --checkers 8 --stats-one-line --stats 0 -v 2>&1 | tail -n 20

# Drop history older than KEEP_DAYS (files first, then the empty date folders).
rclone delete "$DEST/old" --min-age "${KEEP_DAYS}d" --fast-list 2>/dev/null || true
rclone rmdirs "$DEST/old" --leave-root 2>/dev/null || true

echo "backup done: $SRC -> $DEST/current ($STAMP)"
