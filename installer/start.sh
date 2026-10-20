#!/bin/sh
# ReckonGrid im Browser starten. Andreas Meyer, ame@sellerbach.de
set -eu
HERE=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
APP="$HERE/app"
if [ ! -f "$APP/index.html" ]; then
  echo "App-Dateien fehlen: $APP" >&2
  exit 1
fi
PORT=4173
while [ "$PORT" -lt 4190 ]; do
  if ! ss -ltn 2>/dev/null | grep -q ":${PORT} " && ! netstat -ltn 2>/dev/null | grep -q ":${PORT} "; then
    break
  fi
  PORT=$((PORT + 1))
done
URL="http://127.0.0.1:${PORT}/"
if command -v xdg-open >/dev/null 2>&1; then
  (sleep 0.4 && xdg-open "$URL") >/dev/null 2>&1 &
elif command -v open >/dev/null 2>&1; then
  (sleep 0.4 && open "$URL") >/dev/null 2>&1 &
fi
echo "ReckonGrid läuft auf $URL  (Strg+C beendet die App)"
exec python3 -m http.server "$PORT" --bind 127.0.0.1 --directory "$APP"
