from typing import Optional

from pydantic import BaseModel


class UploadResponse(BaseModel):
    task_id: str
    status: str
    message: str


class StatusResponse(BaseModel):
    task_id: str
    status: str
    progress: float
    stage: Optional[str] = None
    has_doc: bool = False
    download_url: Optional[str] = None
    subtitle_url: Optional[str] = None
    error_message: Optional[str] = None


class ErrorResponse(BaseModel):
    detail: str
