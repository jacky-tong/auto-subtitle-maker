from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional
import uuid


class TaskStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    error = "error"


class ProcessingStage(str, Enum):
    extracting_audio = "extracting_audio"
    transcribing = "transcribing"
    translating = "translating"
    aligning = "aligning"
    rendering = "rendering"


@dataclass
class TaskInfo:
    task_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    status: TaskStatus = TaskStatus.pending
    stage: Optional[ProcessingStage] = None
    progress: float = 0.0
    upload_filename: str = ""
    has_doc: bool = False
    bilingual: bool = False
    subtitle_color: str = "#000000"
    error_message: Optional[str] = None
    download_url: Optional[str] = None
    subtitle_url: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Internal paths (not exposed to frontend)
    video_path: str = ""
    doc_path: Optional[str] = None
    audio_path: str = ""
    srt_path: str = ""
    output_video_path: str = ""


class TaskStore:
    def __init__(self) -> None:
        self._tasks: Dict[str, TaskInfo] = {}

    def create(self, info: TaskInfo) -> None:
        self._tasks[info.task_id] = info

    def get(self, task_id: str) -> Optional[TaskInfo]:
        return self._tasks.get(task_id)

    def update(self, task_id: str, **kwargs) -> None:
        if task := self._tasks.get(task_id):
            for key, value in kwargs.items():
                if hasattr(task, key):
                    setattr(task, key, value)

    def delete(self, task_id: str) -> None:
        self._tasks.pop(task_id, None)
