<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-blue?style=flat-square&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.115+-teal?style=flat-square&logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/Whisper-OpenAI-orange?style=flat-square&logo=openai" alt="Whisper">
  <img src="https://img.shields.io/badge/FFmpeg-required-green?style=flat-square&logo=ffmpeg" alt="FFmpeg">
  <img src="https://img.shields.io/badge/license-MIT-purple?style=flat-square" alt="License">
</p>

<h1 align="center">SubtitleForge</h1>
<p align="center"><strong>智能视频字幕自动生成与合成工具</strong></p>
<p align="center">AI-Powered Video Subtitle Generation &amp; Synthesis</p>
<p align="center">Upload a video → Auto speech-to-text or script alignment → Download video with burned-in subtitles</p>

<p align="center">
  <sub>Author: <a href="https://github.com/jacky-tong">我的token都去哪了</a></sub>
</p>

---

## Features

### 🎙️ Auto Speech Recognition (Case B — No Script)
Upload a video without any script. The system uses **OpenAI Whisper**, a state-of-the-art deep learning model, to automatically extract the audio track and generate word-level timestamps. Whisper delivers industry-leading accuracy for Chinese speech recognition and handles mixed Chinese-English scenarios.

**How it works:**
1. FFmpeg extracts the audio track as 16kHz mono WAV
2. Whisper transcribes the audio with precise word-level timestamps
3. The transcribed text is split into readable subtitle lines (intelligently respecting word boundaries)
4. FFmpeg burns the subtitles directly into the video

### 📝 Forced Script Alignment (Case A — With Script)
If you already have a script (.docx or .txt), upload it alongside the video. The system uses a **Smith-Waterman local alignment algorithm** at the character level to precisely map every sentence in your script to the correct timestamp on the video timeline.

**How it works:**
1. The document is parsed into sentences
2. Whisper still runs to detect speech timing and word boundaries
3. The Smith-Waterman algorithm aligns script characters against Whisper's output, tolerating ASR errors
4. Each script sentence gets accurate start/end timestamps mapped from the alignment path
5. The subtitles follow your script exactly — what you wrote is what appears on screen

### ✂️ Smart Line Splitting
Subtitles are split at natural boundaries: **Chinese punctuation marks, spaces, and word boundaries**. English words like "python" are NEVER split across lines. The splitting algorithm searches for the optimal break point near the character limit, preferring punctuation > space > word boundary, with a hard fallback limit.

### 🎨 Customizable Subtitle Style
- **Default:** Black text with white outline (2px) — highly readable on any video background
- **Color picker:** Choose any subtitle text color via the built-in color selector
- **Style:** Rendered via FFmpeg ASS subtitle filter (Arial, 18px, bottom-centered)

### 🌐 Bilingual Subtitles (Chinese + English)
Toggle on to add English subtitles below each Chinese line. Translation is powered by **MyMemory** (free, no API key required). Eight concurrent translation workers process subtitle entries in parallel for speed. Chinese timing and display remain **completely independent** of the bilingual toggle.

### ⚡ GPU Acceleration
Toggle GPU acceleration to run Whisper inference on **CUDA**-enabled NVIDIA GPUs. Speeds up transcription significantly compared to CPU inference.

---

## Quick Start

### Prerequisites

- **Python** 3.8+
- **FFmpeg** (must be in PATH or auto-detected from conda)

```bash
# macOS
brew install ffmpeg

# Windows
winget install ffmpeg

# Ubuntu / Debian
sudo apt install ffmpeg
```

### Install & Run

```bash
# 1. Clone
git clone https://github.com/jacky-tong/auto-subtitle-maker.git
cd auto-subtitle-maker

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start server
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

**Or double-click `启动.bat`** (Windows) to auto-install dependencies, start the server, and open the browser.

Open **http://localhost:8000** in your browser.

On first launch, Whisper downloads the model automatically (tiny: ~72MB, medium: ~1.4GB).

---

## How It Works

```
Upload Video (+ optional Script)
      │
      ▼
┌──────────────────┐
│ 1. Extract Audio  │  FFmpeg → 16kHz mono WAV
└────────┬─────────┘
         ▼
┌──────────────────┐
│ 2. Transcribe     │  Whisper → word-level timestamps
└────────┬─────────┘
         ▼
    ┌────┴────┐
    │ Script?  │
    └────┬────┘
   Yes  │  No
   ┌────┴────┐
   │ Smith-  │  Direct
   │Waterman │  Whisper
   └────┬────┘
        ▼
┌──────────────────┐
│ 3. Translate      │  (if bilingual) MyMemory 8× parallel
│    + Build SRT    │  Smart line splitting
└────────┬─────────┘
         ▼
┌──────────────────┐
│ 4. Burn Subtitles │  FFmpeg ASS filter → hard subtitles
└──────────────────┘
         │
         ▼
   subtitled_video.mp4  +  subtitle.srt
```

---

## Tech Stack

| Component | Technology | Role |
|-----------|-----------|------|
| Backend | **FastAPI** | HTTP API + async task orchestration |
| Speech Recognition | **OpenAI Whisper** | Audio transcription + word timestamps |
| Forced Alignment | **Smith-Waterman** | Character-level script-to-timeline mapping |
| Video Processing | **FFmpeg** | Audio extraction + subtitle burning |
| Translation | **MyMemory** | Free bilingual translation (China-accessible) |
| Document Parsing | **python-docx** | .docx / .txt reading |
| Frontend | **Vanilla HTML/CSS/JS** | Zero-dependency single-file UI with SVG icons |

---

## Configuration

Edit `config.py` to customize:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `WHISPER_MODEL_SIZE` | `medium` | Model size: tiny / base / small / medium / large-v3 |
| `WHISPER_LANGUAGE` | `zh` | Recognition language (99 supported) |
| `WHISPER_DEVICE` | `cpu` | Inference device: cpu / cuda (toggle in UI) |
| `MAX_UPLOAD_SIZE_MB` | `500` | Max upload file size |
| `CLEANUP_AGE_HOURS` | `6` | Auto-delete processed files after N hours |

**Model recommendations:** `tiny` for quick testing (fastest, least accurate), `medium` for daily use (balanced), `large-v3` for best accuracy (needs GPU + memory).

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/upload` | Upload video (+ optional doc, bilingual toggle, color, GPU toggle) |
| `GET` | `/api/task/{id}` | Poll processing status, progress, stage, download URLs |
| `GET` | `/api/download/video/{id}` | Download the subtitled video (MP4) |
| `GET` | `/api/download/subtitle/{id}` | Download the raw SRT subtitle file |
| `DELETE` | `/api/task/{id}` | Delete task and all associated files |

---

## Project Structure

```
auto-subtitle-maker/
├── main.py                  # FastAPI app entry point
├── config.py                # Global settings + ffmpeg auto-detection
├── requirements.txt         # Python dependencies
├── 启动.bat                  # Windows one-click launcher
├── routers/
│   └── api.py               # HTTP endpoints (upload, status, download)
├── models/
│   ├── task.py              # Task state machine + in-memory store
│   └── schemas.py           # Pydantic request/response models
├── services/
│   ├── pipeline.py          # Processing orchestrator (5 stages)
│   ├── whisper_service.py   # Whisper wrapper with device switching
│   ├── aligner.py           # Smith-Waterman forced alignment ★
│   ├── subtitle_service.py  # SRT builder + smart line splitting
│   ├── video_service.py     # FFmpeg subprocess (audio + burn)
│   ├── translation_service.py  # MyMemory parallel translation
│   ├── doc_parser.py        # .docx / .txt → sentence list
│   └── file_manager.py      # Periodic file cleanup
├── utils/
│   └── text_utils.py        # Chinese sentence splitting, normalization
├── static/
│   └── index.html           # Single-page frontend (SVG icons, a11y)
└── storage/                 # Upload & output directories
```

---

## Subtitle Style

```
Font: Arial, 18px
Text color: Configurable (default black #000000)
Outline: White, 2px width
Border style: Outline (BorderStyle=1)
Alignment: Bottom-center (Alignment=2)
Format: ASS (rendered by FFmpeg subtitles filter)
```

---

## License

MIT License — free to use, modify, and distribute.

---

<p align="center"><sub>Built with ❤️ by <a href="https://github.com/jacky-tong">我的token都去哪了</a></sub></p>
