from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from models.task import TaskStore
from services.whisper_service import WhisperService
from services.aligner import ForcedAligner
from services.video_service import VideoService
from services.file_manager import FileManager
from services.pipeline import ProcessingPipeline
from routers.api import router as api_router

# Global singletons
task_store = TaskStore()
file_manager = FileManager()
whisper_svc: Optional[WhisperService] = None
pipeline: Optional[ProcessingPipeline] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global whisper_svc, pipeline

    # Startup: load Whisper model and wire dependencies
    print("Loading Whisper model...")
    whisper_svc = WhisperService()
    aligner = ForcedAligner()
    video_svc = VideoService()
    pipeline = ProcessingPipeline(
        whisper_svc=whisper_svc,
        aligner=aligner,
        video_svc=video_svc,
    )
    await file_manager.start_cleanup_loop()
    print("Server ready. Whisper model loaded.")
    yield

    # Shutdown
    await file_manager.stop_cleanup_loop()


app = FastAPI(
    title="智能视频字幕生成与合成系统",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.mount("/", StaticFiles(directory="static", html=True), name="static")
