#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
entry="clone_server.py"
if [[ "${1:-}" == "--ui" ]]; then
  entry="ui.py"
  shift
fi

if command -v py >/dev/null 2>&1; then
  exec py -3 "$script_dir/$entry" "$@"
elif command -v python3 >/dev/null 2>&1; then
  exec python3 "$script_dir/$entry" "$@"
elif command -v python >/dev/null 2>&1; then
  exec python "$script_dir/$entry" "$@"
else
  echo "Python 3 is required to run clone_server.py" >&2
  exit 127
fi
