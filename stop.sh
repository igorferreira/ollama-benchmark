#!/usr/bin/env bash
set -euo pipefail
script_dir=$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
for interpreter in python3 python; do
  if command -v "$interpreter" >/dev/null 2>&1 && "$interpreter" -c 'import sys; raise SystemExit(sys.version_info < (3, 11))' 2>/dev/null; then
    exec "$interpreter" "$script_dir/scripts/service.py" stop "$@"
  fi
done
printf '%s\n' 'Python 3.11 ou superior nao encontrado.' >&2
exit 1
