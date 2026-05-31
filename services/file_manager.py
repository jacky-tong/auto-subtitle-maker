from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path
from typing import Optional

from config import UPLOAD_DIR, OUTPUT_DIR, TEMP_DIR, CLEANUP_AGE_HOURS


class FileManager:
    def __init__(self) -> None:
        self._cleanup_task: asyncio.Task | None = None

    async def start_cleanup_loop(self) -> None:
        """Periodically clean up old files. Runs every 30 minutes."""
        async def _loop() -> None:
            while True:
                await asyncio.sleep(1800)
                await self._cleanup()

        self._cleanup_task = asyncio.create_task(_loop())

    async def stop_cleanup_loop(self) -> None:
        if self._cleanup_task:
            self._cleanup_task.cancel()
            self._cleanup_task = None

    async def _cleanup(self) -> None:
        cutoff = time.time() - CLEANUP_AGE_HOURS * 3600
        for directory in [UPLOAD_DIR, OUTPUT_DIR, TEMP_DIR]:
            try:
                for entry in directory.iterdir():
                    if entry.is_file() and entry.stat().st_mtime < cutoff:
                        entry.unlink()
            except Exception:
                pass

    @staticmethod
    def cleanup_task_files(task_id: str) -> None:
        """Delete all files associated with a specific task ID."""
        for directory in [UPLOAD_DIR, OUTPUT_DIR, TEMP_DIR]:
            try:
                for entry in directory.iterdir():
                    if entry.is_file() and task_id in entry.stem:
                        entry.unlink()
            except Exception:
                pass

    @staticmethod
    def safe_path(directory: Path, filename: str) -> str:
        """Build a safe file path, preventing path traversal."""
        safe_name = Path(filename).name
        return str(directory / safe_name)
