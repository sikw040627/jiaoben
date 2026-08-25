#!/system/bin/sh
# autorun.sh — on-device runner. Download a recorded script from the autoauto
# cloud server and run it, entirely on the phone (Termux) with no PC / ADB.
#
# Usage:
#   sh autorun.sh <base_url> <name> [--run|--download-only] [--token <t>]
#
# Examples:
#   sh autorun.sh http://192.168.1.10:8000 daily_task
#   sh autorun.sh http://192.168.1.10:8000 daily_task --download-only
#
# Scripts are cached under $AUTOAUTO_STORE (default ~/autoauto-store).

BASE="$1"
NAME="$2"
ACTION="${3:---run}"
TOKEN=""
if [ "$4" = "--token" ]; then TOKEN="$5"; fi

if [ -z "$BASE" ] || [ -z "$NAME" ]; then
  echo "usage: sh autorun.sh <base_url> <name> [--run|--download-only] [--token <t>]" >&2
  exit 2
fi

DIR="${AUTOAUTO_STORE:-$HOME/autoauto-store}"
mkdir -p "$DIR"
OUT="$DIR/$NAME.sh"
URL="$BASE/scripts/$NAME"

echo "downloading $NAME <- $BASE"
if command -v curl >/dev/null 2>&1; then
  if [ -n "$TOKEN" ]; then
    curl -fsSL -H "Authorization: Bearer $TOKEN" "$URL" -o "$OUT" || { echo "download failed" >&2; exit 1; }
  else
    curl -fsSL "$URL" -o "$OUT" || { echo "download failed" >&2; exit 1; }
  fi
elif command -v wget >/dev/null 2>&1; then
  if [ -n "$TOKEN" ]; then
    wget -q --header="Authorization: Bearer $TOKEN" -O "$OUT" "$URL" || { echo "download failed" >&2; exit 1; }
  else
    wget -qO "$OUT" "$URL" || { echo "download failed" >&2; exit 1; }
  fi
else
  echo "need curl or wget (Termux: pkg install curl)" >&2
  exit 1
fi

echo "saved -> $OUT"
if [ "$ACTION" = "--run" ]; then
  echo "running $NAME ..."
  sh "$OUT"
fi
