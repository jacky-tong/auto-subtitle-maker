from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

UPLOAD_DIR = PROJECT_ROOT / "storage" / "uploads"
OUTPUT_DIR = PROJECT_ROOT / "storage" / "outputs"
TEMP_DIR = PROJECT_ROOT / "storage" / "temp"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)

WHISPER_MODEL_SIZE: str = "tiny"
WHISPER_DEVICE: str = "cpu"
WHISPER_LANGUAGE: str = "zh"

FFMPEG_PATH: str = "ffmpeg"
FFPROBE_PATH: str = "ffprobe"

MAX_UPLOAD_SIZE_MB: int = 500
CLEANUP_AGE_HOURS: int = 6

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
ALLOWED_DOC_EXTENSIONS = {".docx", ".txt"}

HOST: str = "0.0.0.0"
PORT: int = 8000
