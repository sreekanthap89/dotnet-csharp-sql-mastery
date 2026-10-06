from pathlib import Path
import os

# Base directory for InterviewAssist
BASE_DIR = Path(__file__).resolve().parent.parent

# Data storage directories
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
STORAGE_DIR = DATA_DIR / "storage"

# Workspace parent directory (where the 37+ C# learning files live)
WORKSPACE_DIR = BASE_DIR.parent

# Ensure directories exist
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# Application Settings & Persistence
DEFAULT_HOST = os.environ.get("HOST", "127.0.0.1")
DEFAULT_PORT = int(os.environ.get("PORT", "8000"))
SETTINGS_FILE = STORAGE_DIR / "app_settings.json"

# Default Provider Settings
DEFAULT_OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
DEFAULT_LM_STUDIO_URL = os.environ.get("LM_STUDIO_URL", "http://localhost:1234/v1")
DEFAULT_OPENROUTER_URL = os.environ.get("OPENROUTER_URL", "https://openrouter.ai/api/v1")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

