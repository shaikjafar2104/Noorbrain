#!/usr/bin/env bash

cd ~/Projects/NoorBrain || exit 1
set +e

BACKUP=$(
  cat /tmp/v126-a2-rollback-path 2>/dev/null
)

if [ -z "$BACKUP" ] || [ ! -f "$BACKUP" ]; then
    echo "ROLLBACK BACKUP NOT FOUND"
    exit 1
fi

cp "$BACKUP" \
   dashboard/mobile/index.html

echo "V12.6-A2 MOBILE HTML ROLLED BACK"
echo "Refresh/reopen phone app."
