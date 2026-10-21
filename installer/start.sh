#!/bin/sh
# ReckonGrid im Browser starten. Andreas Meyer, ame@sellerbach.de
set -eu
HERE=$(CDPATH= cd -- "$(dirname "$0")" && pwd)

if [ -n "${1:-}" ]; then
  APP=$1
elif [ -f "$HERE/app/index.html" ]; then
  APP="$HERE/app"
elif [ -f "$HERE/dist/index.html" ]; then
  APP="$HERE/dist"
elif [ -f "$HERE/../dist/index.html" ]; then
  APP="$HERE/../dist"
else
  echo "Keine gebaute App gefunden (index.html fehlt)." >&2
  echo "index.html nicht doppelklicken: der Browser blockiert Module über file://." >&2
  echo "Entwicklung: npm install && npm run dev" >&2
  echo "Die Entwicklungsumgebung liegt auf http://127.0.0.1:5173/" >&2
  exit 1
fi

APP=$(CDPATH= cd -- "$APP" && pwd)
if [ ! -f "$APP/index.html" ]; then
  echo "App-Dateien fehlen: $APP" >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 wurde nicht gefunden." >&2
  echo "Bitte Python 3 installieren, oder im Quelltext npm install && npm run dev ausführen." >&2
  exit 1
fi

PORT=4173
while [ "$PORT" -lt 4190 ]; do
  if python3 -c 'import socket,sys
s=socket.socket()
try:
    s.bind(("127.0.0.1", int(sys.argv[1])))
except OSError:
    sys.exit(1)
finally:
    s.close()
' "$PORT"; then
    break
  fi
  PORT=$((PORT + 1))
done
if [ "$PORT" -ge 4190 ]; then
  echo "Kein freier Port zwischen 4173 und 4189." >&2
  exit 1
fi

URL="http://127.0.0.1:${PORT}/"
echo "ReckonGrid läuft auf $URL"
echo "Strg+C beendet die App."

(
  i=0
  while [ "$i" -lt 50 ]; do
    if command -v curl >/dev/null 2>&1; then
      if curl -sf -o /dev/null "$URL"; then
        break
      fi
    else
      sleep 0.4
      break
    fi
    i=$((i + 1))
    sleep 0.1
  done
  if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$URL" >/dev/null 2>&1 || true
  elif command -v open >/dev/null 2>&1; then
    open "$URL" >/dev/null 2>&1 || true
  else
    echo "Browser bitte manuell öffnen: $URL"
  fi
) &

exec python3 -m http.server "$PORT" --bind 127.0.0.1 --directory "$APP"
