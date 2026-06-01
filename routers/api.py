import asyncio
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, UploadFile, HTTPException, Form, Depends
from fastapi.responses import FileResponse

from models.task import TaskInfo, TaskStatus, TaskStore
from models.schemas import UploadResponse, StatusResponse, ErrorResponse
from services.pipeline import ProcessingPipeline
from services.file_manager import FileManager
from config import (
    UPLOAD_DIR, OUTPUT_DIR, TEMP_DIR,
    ALLOWED_VIDEO_EXTENSIONS, ALLOWED_DOC_EXTENSIONS,
    MAX_UPLOAD_SIZE_MB,
)

router = APIRouter(prefix="/api")


def get_task_store() -> TaskStore:
    from main import task_store
    return task_store


def get_pipeline() -> ProcessingPipeline:
    from main import pipeline
    return pipeline


def get_file_manager() -> FileManager:
    from main import file_manager
    return file_manager


@router.post("/upload", response_model=UploadResponse)
async def upload(
    video: UploadFile = File(...),
    doc: Optional[UploadFile] = File(default=None),
    bilingual: bool = Form(default=False),
    subtitle_color: str = Form(default="#000000"),
    task_store: TaskStore = Depends(get_task_store),
    pipeline_svc: ProcessingPipeline = Depends(get_pipeline),
):
    # Validate video extension
    video_ext = Path(video.filename or "").suffix.lower()
    if video_ext not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported video format: {video_ext}. Allowed: {', '.join(ALLOWED_VIDEO_EXTENSIONS)}",
        )

    # Validate doc extension if provided
    if doc and doc.filename:
        doc_ext = Path(doc.filename).suffix.lower()
        if doc_ext not in ALLOWED_DOC_EXTENSIONS:
            raise HTTPException(
                status_code=422,
                detail=f"Unsupported document format: {doc_ext}. Allowed: {', '.join(ALLOWED_DOC_EXTENSIONS)}",
            )

    # Create task
    task_id = uuid.uuid4().hex[:12]

    # Save video
    video_name = f"{task_id}_video{video_ext}"
    video_path = str(UPLOAD_DIR / video_name)
    content = await video.read()
    if len(content) > MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File too large. Max {MAX_UPLOAD_SIZE_MB}MB.")
    with open(video_path, "wb") as f:
        f.write(content)

    # Save doc if provided
    doc_path: Optional[str] = None
    has_doc = False
    if doc and doc.filename:
        doc_ext = Path(doc.filename).suffix.lower()
        doc_name = f"{task_id}_doc{doc_ext}"
        doc_path = str(UPLOAD_DIR / doc_name)
        content = await doc.read()
        with open(doc_path, "wb") as f:
            f.write(content)
        has_doc = True

    # Create and store task
    task_info = TaskInfo(
        task_id=task_id,
        upload_filename=video.filename or "unknown",
        has_doc=has_doc,
        bilingual=bilingual,
        subtitle_color=subtitle_color,
        video_path=video_path,
        doc_path=doc_path,
    )
    task_store.create(task_info)

    # Start background processing
    asyncio.create_task(pipeline_svc.run(task_info, task_store))

    return UploadResponse(
        task_id=task_id,
        status="pending",
        message="File received, processing started.",
    )


@router.get("/task/{task_id}", response_model=StatusResponse)
async def get_status(
    task_id: str,
    task_store: TaskStore = Depends(get_task_store),
):
    info = task_store.get(task_id)
    if not info:
        raise HTTPException(status_code=404, detail="Task not found")

    return StatusResponse(
        task_id=info.task_id,
        status=info.status.value,
        progress=info.progress,
        stage=info.stage.value if info.stage else None,
        has_doc=info.has_doc,
        download_url=info.download_url,
        subtitle_url=info.subtitle_url,
        error_message=info.error_message,
    )


@router.get("/download/video/{task_id}")
async def download_video(
    task_id: str,
    task_store: TaskStore = Depends(get_task_store),
):
    info = task_store.get(task_id)
    if not info:
        raise HTTPException(status_code=404, detail="Task not found")
    if info.status != TaskStatus.completed:
        raise HTTPException(status_code=400, detail="Task not yet completed")
    if not info.output_video_path or not Path(info.output_video_path).exists():
        raise HTTPException(status_code=404, detail="Output video not found")

    return FileResponse(
        info.output_video_path,
        media_type="video/mp4",
        filename=f"subtitled_{info.upload_filename}",
    )


@router.get("/download/subtitle/{task_id}")
async def download_subtitle(
    task_id: str,
    task_store: TaskStore = Depends(get_task_store),
):
    info = task_store.get(task_id)
    if not info:
        raise HTTPException(status_code=404, detail="Task not found")
    if not info.srt_path or not Path(info.srt_path).exists():
        raise HTTPException(status_code=404, detail="Subtitle file not found")

    return FileResponse(
        info.srt_path,
        media_type="text/plain",
        filename=f"subtitle_{task_id}.srt",
    )


@router.delete("/task/{task_id}")
async def delete_task(
    task_id: str,
    task_store: TaskStore = Depends(get_task_store),
    fm: FileManager = Depends(get_file_manager),
):
    if not task_store.get(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    FileManager.cleanup_task_files(task_id)
    task_store.delete(task_id)
    return {"ok": True}
