#!/bin/bash
set -euo pipefail

# Build script for DigitalOcean Functions Python runtime
# Creates a virtualenv and installs dependencies into it so the runtime
# can import packaged libraries without network access at invocation time.

if [ -d "virtualenv" ]; then
  rm -rf "virtualenv"
fi

if ! command -v virtualenv >/dev/null 2>&1; then
  echo "Error: virtualenv command not found. Install it with 'pip install virtualenv'." >&2
  exit 1
fi

PYTHON_BIN=${PYTHON_BIN:-python3.11}
if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  if command -v python3 >/dev/null 2>&1; then
    echo "PYTHON_BIN ${PYTHON_BIN} not found. Falling back to python3." >&2
    PYTHON_BIN=$(command -v python3)
  else
    echo "Error: Python interpreter ${PYTHON_BIN} not found and python3 unavailable." >&2
    exit 1
  fi
fi

PYTHON_ABI=$("${PYTHON_BIN}" -c 'import sys; print(f"python{sys.version_info.major}.{sys.version_info.minor}")')
if [ "${PYTHON_ABI}" != "python3.11" ]; then
  echo "Warning: Using ${PYTHON_ABI}. DigitalOcean runtime is python3.11." >&2
fi

virtualenv --python="${PYTHON_BIN}" --without-pip virtualenv
"${PYTHON_BIN}" -m pip install --no-cache-dir -r requirements.txt --target "virtualenv/lib/${PYTHON_ABI}/site-packages"

SITE_PACKAGES="virtualenv/lib/${PYTHON_ABI}/site-packages"

# Remove bulky discovery cache data bundled with google-api-python-client.
if [ -d "${SITE_PACKAGES}/googleapiclient/discovery_cache" ]; then
  find "${SITE_PACKAGES}/googleapiclient/discovery_cache" -mindepth 1 -delete
fi

# Trim Python bytecode caches to keep deployment size minimal.
find "${SITE_PACKAGES}" -type d -name "__pycache__" -prune -exec rm -rf {} +
find "${SITE_PACKAGES}" -name "*.pyc" -delete
