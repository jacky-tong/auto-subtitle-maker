from __future__ import annotations

import subprocess
import asyncio
from pathlib import Path

from config import FFMPEG_PATH, FFPROBE_PATH


class VideoService:
    def __init__(self, ffmpeg_path: str = "", ffprobe_path: str = "") -> None:
        self._ffmpeg = ffmpeg_path or FFMPEG_PATH
        self._ffprobe = ffprobe_path or FFPROBE_PATH

    def extract_audio(self, video_path: str, output_wav_path: str) -> None:
        """Extract audio from video as 16kHz mono WAV for Whisper."""
        cmd = [
            self._ffmpeg,
            "-i", video_path,
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            "-y",
            output_wav_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Audio extraction failed: {result.stderr}")

    @staticmethod
    def _hex_to_ass(hex_color: str) -> str:
        """Convert #RRGGBB to ASS &HBBGGRR00 format."""
        c = hex_color.lstrip("#")
        if len(c) == 6:
            r, g, b = c[0:2], c[2:4], c[4:6]
            return f"&H00{b}{g}{r}00"
        return "&H00000000"  # default black

    async def burn_subtitles(
        self,
        video_path: str,
        srt_path: str,
        output_path: str,
        subtitle_color: str = "#000000",
    ) -> None:
        """Burn subtitles into video with configurable text color and white outline."""
        primary = self._hex_to_ass(subtitle_color)

        style = (
            "FontName=Arial,"
            "FontSize=18,"
            f"PrimaryColour={primary},"
            "OutlineColour=&H00FFFFFF,"
            "Outline=2,"
            "BorderStyle=1,"
            "Shadow=0,"
            "Alignment=2"
        )

        escaped_srt = str(Path(srt_path).as_posix()).replace(":", "\\:")
        vf = f"subtitles='{escaped_srt}':force_style='{style}'"

        cmd = [
            self._ffmpeg,
            "-i", video_path,
            "-vf", vf,
            "-c:a", "copy",
            "-y",
            output_path,
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        _, stderr = await process.communicate()

        if process.returncode != 0:
            err_text = stderr.decode("utf-8", errors="replace")
            raise RuntimeError(f"Subtitle burning failed: {err_text}")
