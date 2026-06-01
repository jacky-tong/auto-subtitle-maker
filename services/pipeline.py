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
from services.translation_service import TranslationService
from services.file_manager import FileManager
from config import UPLOAD_DIR, OUTPUT_DIR, TEMP_DIR


class ProcessingPipeline:
    # Delimiter used to join sentences for batch translation
    _SENT_DELIM = " ||| "

    def __init__(
        self,
        whisper_svc: WhisperService,
        aligner: ForcedAligner,
        video_svc: VideoService,
    ) -> None:
        self.whisper = whisper_svc
        self.aligner = aligner
        self.video = video_svc
        self.translator = TranslationService()

    async def _add_bilingual(
        self, entries: list[SubtitleEntry]
    ) -> list[SubtitleEntry]:
        """Translate entries sentence-by-sentence for natural bilingual display.

        Strategy:
        1. Collect all Chinese text, split into complete sentences by punctuation
        2. Map each sentence back to its subtitle entries
        3. Translate each complete sentence → one English sentence
        4. Assign the English sentence to all entries of that sentence

        Result: one Chinese sentence maps to exactly one English sentence,
        displayed as two lines (Chinese top, English bottom).
        """
        # 1. Join all texts, split into complete sentences
        full_text = "".join(e.text for e in entries)
        from utils.text_utils import split_sentences
        sentences = split_sentences(full_text)
        if not sentences:
            return entries

        # 2. Map each entry → sentence index
        entry_sent_idx: list[int] = []
        char_ptr = 0
        sent_idx = 0
        sent_start = 0
        for entry in entries:
            entry_len = len(entry.text)
            # Find which sentence contains the midpoint of this entry
            mid = char_ptr + entry_len // 2
            while sent_idx < len(sentences) - 1:
                next_start = sent_start + len(sentences[sent_idx])
                if mid < next_start:
                    break
                sent_start = next_start
                sent_idx += 1
            entry_sent_idx.append(sent_idx)
            char_ptr += entry_len

        # 3. Batch translate all complete sentences (fast)
        translated = await self.translator.translate_batch_async(sentences)

        # 4. Build sentence-level English text, assign to entries
        sent_en_map: dict[int, str] = {}
        for i, en in enumerate(translated):
            if en.strip():
                sent_en_map[i] = en.strip()

        for i, entry in enumerate(entries):
            sidx = entry_sent_idx[i]
            entry.text_en = sent_en_map.get(sidx, "")

        return entries

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
            segments = await asyncio.to_thread(
                self.whisper.transcribe, audio_path, task_info.use_gpu
            )

            if not segments:
                raise RuntimeError("Whisper returned no speech segments. The video may have no audio track.")

            # Stage 3: Branch Case A (doc) or Case B (no doc)
            entries: list[SubtitleEntry]
            if task_info.has_doc and task_info.doc_path:
                task_store.update(task_id, stage=ProcessingStage.aligning, progress=40.0)
                doc_sentences = DocParser.parse(task_info.doc_path)
                aligned = self.aligner.align(doc_sentences, segments)
                entries = [
                    SubtitleEntry(text=a.text, start=a.start, end=a.end)
                    for a in aligned
                ]
            else:
                task_store.update(task_id, progress=40.0)
                entries = []
                for seg in segments:
                    if seg.text.strip():
                        entries.append(SubtitleEntry(
                            text=seg.text.strip(),
                            start=seg.start,
                            end=seg.end,
                        ))

            # Stage 3.5: Translate if bilingual
            if task_info.bilingual:
                task_store.update(task_id, stage=ProcessingStage.translating, progress=50.0)
                entries = await self._add_bilingual(entries)

            # Stage 4: Build SRT
            task_store.update(task_id, progress=65.0)
            srt_content = SubtitleService.build_srt(entries, bilingual=task_info.bilingual)
            srt_path = str(TEMP_DIR / f"{task_id}_subtitle.srt")
            task_info.srt_path = srt_path
            with open(srt_path, "w", encoding="utf-8") as f:
                f.write(srt_content)

            # Stage 5: Burn subtitles into video
            task_store.update(task_id, stage=ProcessingStage.rendering, progress=70.0)
            output_path = str(OUTPUT_DIR / f"{task_id}_subtitled.mp4")
            task_info.output_video_path = output_path
            await self.video.burn_subtitles(
                task_info.video_path, srt_path, output_path,
                subtitle_color=task_info.subtitle_color,
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
