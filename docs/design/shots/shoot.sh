#!/bin/sh
# Usage: sh shots/shoot.sh 01-command-map  -> shots/01-command-map.png (1600x900)
cd "$(dirname "$0")/.."
f="$1"; w="${2:-1600}"; h="${3:-900}"
"/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" --headless=new --hide-scrollbars \
  --window-size=$w,$h --virtual-time-budget=15000 --allow-file-access-from-files \
  --screenshot="$(cygpath -w "$PWD/shots/$f.png")" "file:///$(cygpath -m "$PWD/screens/$f.html")" >/dev/null 2>&1
ls -la "shots/$f.png" | awk '{print $5, $9}'
