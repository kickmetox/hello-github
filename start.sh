#!/bin/sh
# ReckonGrid aus dem Projektordner starten (nutzt dist/, ohne npm install).
set -eu
HERE=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
exec "$HERE/installer/start.sh" "$@"
