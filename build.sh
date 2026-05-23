#!/usr/bin/env bash
# Build Grasp.app and (optionally) move it into /Applications.
set -euo pipefail

cd "$(dirname "$0")"

PYTHON="${PYTHON:-python3}"

if [ ! -d ".venv" ]; then
    echo "→ Creating virtualenv (.venv)…"
    "$PYTHON" -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo "→ Installing dependencies…"
pip install --upgrade pip >/dev/null
pip install -r requirements.txt
pip install py2app

echo "→ Cleaning previous build…"
rm -rf build dist

echo "→ Building Grasp.app with py2app…"
python setup.py py2app

APP_PATH="dist/Grasp.app"
if [ ! -d "$APP_PATH" ]; then
    echo "Build failed: $APP_PATH not found"
    exit 1
fi

echo
echo "Build complete: $APP_PATH"
echo
read -r -p "Install to /Applications now? [y/N] " ans
if [[ "$ans" =~ ^[Yy]$ ]]; then
    if [ -d "/Applications/Grasp.app" ]; then
        echo "→ Removing existing /Applications/Grasp.app"
        rm -rf "/Applications/Grasp.app"
    fi
    cp -R "$APP_PATH" /Applications/
    echo "Installed to /Applications/Grasp.app"
    echo "Launch with: open /Applications/Grasp.app"
fi
