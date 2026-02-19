#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
#  Build script for Text-to-Speech App
#  Usage: ./build_app.sh
#
#  ⚠️  PyInstaller can only build for the OS it runs on.
#      Run this script on macOS to get a .app,
#      or on Windows (Git Bash / WSL) to get a .exe.
#
#  Produces:
#    macOS   → dist/Text-to-Speech.app  (drag to /Applications)
#    Windows → dist/Text-to-Speech/Text-to-Speech.exe
# ─────────────────────────────────────────────────────────────────
set -e

echo "📦  Syncing dependencies with uv..."
uv sync

echo "🔨  Running PyInstaller..."
uv run pyinstaller tts_app.spec --clean --noconfirm

echo ""
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "✅  macOS build complete → dist/Text-to-Speech.app"
    echo "    Drag it to /Applications or double-click to run."
elif [[ "$OSTYPE" == "msys"* || "$OSTYPE" == "cygwin"* || "$OS" == "Windows_NT" ]]; then
    echo "✅  Windows build complete → dist/Text-to-Speech/Text-to-Speech.exe"
    echo "    Run the .exe directly or zip the dist/Text-to-Speech/ folder to distribute."
else
    echo "✅  Build complete → dist/Text-to-Speech/"
    echo "    Run the binary inside that folder."
fi
