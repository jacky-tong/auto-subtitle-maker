import subprocess
import re
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

    def get_duration(self, video_path: str) -> float:
        """Get video duration in seconds using ffprobe."""
        cmd = [
            self._ffprobe,
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Failed to get video duration: {result.stderr}")
        return float(result.stdout.strip())

    async def burn_subtitles(
        self,
        video_path: str,
        srt_path: str,
        output_path: str,
    ) -> None:
        """Burn subtitles into video with black text and white outline.

        Uses ASS style via FFmpeg subtitles filter for reliable cross-platform rendering.
        """
        # Use ASS style override for black text + white outline
        style = (
            "FontName=Arial,"
            "FontSize=18,"
            "PrimaryColour=&H00000000,"
            "OutlineColour=&H00FFFFFF,"
            "Outline=2,"
            "BorderStyle=1,"
            "Shadow=0,"
            "Alignment=2"
        )

        # FFmpeg subtitles filter: escape Windows paths and use force_style
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
