#!/bin/sh
# Select the installed project/shared virtualenv instead of an arbitrary
# system Python. All remaining arguments are passed to session_capture.
set -eu

if [ -n "${VIRTUAL_ENV:-}" ] && [ -x "${VIRTUAL_ENV}/bin/python" ]; then
  python_bin="${VIRTUAL_ENV}/bin/python"
elif [ -x ".venv/bin/python" ]; then
  python_bin=".venv/bin/python"
elif [ -x "${HOME}/.venv/bin/python" ]; then
  python_bin="${HOME}/.venv/bin/python"
else
  echo "Không tìm thấy .venv/bin/python hoặc ~/.venv/bin/python" >&2
  exit 2
fi

if ! PYTHONPATH=src "$python_bin" -c "import ssi_sdk" 2>/dev/null; then
  echo "Môi trường $python_bin chưa có ssi-sdk. Cài dự án bằng: $python_bin -m pip install -e '.[dev]'" >&2
  exit 2
fi

exec env PYTHONPATH=src "$python_bin" -m ssi_api.session_capture "$@"
