#!/usr/bin/env bash
# Packages the widget_inspector Lambda into a deployable zip.
# Cross-platform: detects PowerShell on Windows (Git Bash), uses `zip` on Linux/Mac.
#
# Run from repo root: bash scripts/build-lambda.sh
#
# IMPORTANT: When dependencies are added later, pip install will use
# --platform manylinux2014_x86_64 so binary wheels match the Lambda runtime.

set -euo pipefail

LAMBDA_DIR="lambda/widget_inspector"
BUILD_DIR="lambda/build"
ZIP_FILE="lambda/widget_inspector.zip"
PYTHON_VERSION="3.12"

echo "==> Cleaning previous build artifacts"
rm -rf "$BUILD_DIR" "$ZIP_FILE"
mkdir -p "$BUILD_DIR"

echo "==> Copying source files"
cp "$LAMBDA_DIR"/*.py "$BUILD_DIR/"

# Install deps if requirements.txt has any non-comment lines
if grep -v '^\s*#' "$LAMBDA_DIR/requirements.txt" 2>/dev/null | grep -v '^\s*$' > /dev/null; then
  echo "==> Installing dependencies for Lambda runtime"
  pip install \
    -r "$LAMBDA_DIR/requirements.txt" \
    --platform manylinux2014_x86_64 \
    --target "$BUILD_DIR" \
    --implementation cp \
    --python-version "$PYTHON_VERSION" \
    --only-binary=:all: \
    --upgrade
else
  echo "==> No runtime dependencies (stub Lambda)"
fi

echo "==> Creating zip"

# Detect zip command — use native `zip` if available, else PowerShell on Windows
if command -v zip > /dev/null 2>&1; then
  (cd "$BUILD_DIR" && zip -r "../widget_inspector.zip" . -q)
elif command -v powershell.exe > /dev/null 2>&1; then
  # Windows fallback via PowerShell Compress-Archive
  # Note: paths need Windows-style for PowerShell
  WIN_BUILD=$(cygpath -w "$BUILD_DIR" 2>/dev/null || echo "$BUILD_DIR")
  WIN_ZIP=$(cygpath -w "$ZIP_FILE" 2>/dev/null || echo "$ZIP_FILE")
  powershell.exe -NoProfile -Command \
    "Compress-Archive -Path '${WIN_BUILD}\\*' -DestinationPath '${WIN_ZIP}' -Force"
else
  echo "ERROR: Neither 'zip' nor PowerShell available. Cannot create archive." >&2
  exit 1
fi

ZIP_SIZE=$(du -h "$ZIP_FILE" 2>/dev/null | cut -f1 || echo "?")
echo "==> Done. Zip: $ZIP_FILE ($ZIP_SIZE)"