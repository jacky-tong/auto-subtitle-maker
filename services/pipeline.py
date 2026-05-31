from __future__ import annotations

import asyncio
import traceback
from pathlib import Path

from models.task import TaskInfo, TaskStatus, TaskStore, ProcessingStage
from services.whisper_service import WhisperService
from services.aligner import ForcedAligner, AlignedSentence
from services.subtitle_service import SubtitleService, SubtitleEntry
from services.video_service import VideoService
from services.doc_parser import DocParser
from services.file_manager import FileManager
from config import UPLOAD_DIR, OUTPUT_DIR, TEMP_DIR


class ProcessingPipeline:
    def __init__(
        self,
        whisper_svc: WhisperService,
        aligner: ForcedAligner,
        video_svc: VideoService,
    ) -> None:
        self.whisper = whisper_svc
        self.aligner = aligner
        self.video = video_svc

    async def run(self, task_info: TaskInfo, task_store: TaskStore) -> None:
        task_id = task_info.task_id
        try:
            # Stage 1: Extract audio
            task_store.update(task_id, stage=ProcessingStage.extracting_audio, progress=5.0)
            audio_path = str(TEMP_DIR / f"{task_id}_audio.wav")
            task_info.audio_path = audio_path
            self.video.extract_audio(task_info.video_path, audio_path)

            # Stage 2: Transcribe with Whisper
            task_store.update(task_id, stage=ProcessingStage.transcribing, progress=15.0)
            segments = await asyncio.to_thread(self.whisper.transcribe, audio_path)

            if not segments:
                raise RuntimeError("Whisper returned no speech segments. The video may have no audio track.")

            # Stage 3: Branch Case A (doc) or Case B (no doc)
            entries: list[SubtitleEntry]
            if task_info.has_doc and task_info.doc_path:
                task_store.update(task_id, stage=ProcessingStage.aligning, progress=50.0)
                doc_sentences = DocParser.parse(task_info.doc_path)
                aligned = self.aligner.align(doc_sentences, segments)
                entries = [
                    SubtitleEntry(text=a.text, start=a.start, end=a.end)
                    for a in aligned
                ]
            else:
                # Case B: Use Whisper output directly
                task_store.update(task_id, stage=ProcessingStage.aligning, progress=50.0)
                entries = []
                for seg in segments:
                    if seg.text.strip():
                        entries.append(SubtitleEntry(
                            text=seg.text.strip(),
                            start=seg.start,
                            end=seg.end,
                        ))

            # Stage 4: Build SRT
            task_store.update(task_id, progress=65.0)
            srt_content = SubtitleService.build_srt(entries)
            srt_path = str(TEMP_DIR / f"{task_id}_subtitle.srt")
            task_info.srt_path = srt_path
            with open(srt_path, "w", encoding="utf-8") as f:
                f.write(srt_content)

            # Stage 5: Burn subtitles into video
            task_store.update(task_id, stage=ProcessingStage.rendering, progress=70.0)
            output_path = str(OUTPUT_DIR / f"{task_id}_subtitled.mp4")
            task_info.output_video_path = output_path
            await self.video.burn_subtitles(
                task_info.video_path, srt_path, output_path
            )

            # Done
            task_store.update(
                task_id,
                status=TaskStatus.completed,
                stage=None,
                progress=100.0,
                download_url=f"/api/download/video/{task_id}",
                subtitle_url=f"/api/download/subtitle/{task_id}",
            )

        except Exception as e:
            tb = traceback.format_exc()
            task_store.update(
                task_id,
                status=TaskStatus.error,
                error_message=f"{e}\n{tb}",
            )
