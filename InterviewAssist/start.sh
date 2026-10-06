#!/usr/bin/env bash
# ==============================================================================
# Interview Assist - 1-Click Universal Launcher (macOS & Linux)
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
VENV_DIR="$BACKEND_DIR/venv"

echo "========================================================"
echo "  🚀 Starting Interview Assist (RAG Interview Platform) "
echo "========================================================"

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 is not installed or not in PATH."
    echo "Please install Python 3.9+ from https://www.python.org"
    exit 1
fi

# Set up virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 Creating virtual environment in $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Install or upgrade dependencies
echo "🔍 Checking dependencies..."
pip install -q -r "$BACKEND_DIR/requirements.txt"

# Open the browser in background after server starts
(
    sleep 2
    URL="http://localhost:8000"
    echo "🌐 Opening Interview Assist in your default browser: $URL"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        open "$URL"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        xdg-open "$URL" &> /dev/null || sensible-browser "$URL" &> /dev/null || true
    fi
) &

echo "✨ Launching server on http://localhost:8000 ..."
echo "Press Ctrl+C to stop."
cd "$BACKEND_DIR"
python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload
