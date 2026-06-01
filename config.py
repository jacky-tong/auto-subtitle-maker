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

import shutil

def _find_ffmpeg() -> str:
    """Auto-detect ffmpeg in PATH or common install locations."""
    path = shutil.which("ffmpeg")
    if path:
        return path
    candidates = [
        Path.home() / "miniconda3" / "Library" / "bin" / "ffmpeg.exe",
        Path.home() / "miniconda3" / "Scripts" / "ffmpeg.exe",
        Path("C:/ffmpeg/bin/ffmpeg.exe"),
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return "ffmpeg"

def _find_ffprobe() -> str:
    path = shutil.which("ffprobe")
    if path:
        return path
    ff_dir = Path(_find_ffmpeg()).parent
    probe = ff_dir / "ffprobe.exe"
    if probe.exists():
        return str(probe)
    return "ffprobe"

FFMPEG_PATH: str = _find_ffmpeg()
FFPROBE_PATH: str = _find_ffprobe()

MAX_UPLOAD_SIZE_MB: int = 500
CLEANUP_AGE_HOURS: int = 6

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
ALLOWED_DOC_EXTENSIONS = {".docx", ".txt"}

HOST: str = "0.0.0.0"
PORT: int = 8000
