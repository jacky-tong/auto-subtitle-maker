from __future__ import annotations

from dataclasses import dataclass, field
import whisper

from config import WHISPER_MODEL_SIZE, WHISPER_DEVICE, WHISPER_LANGUAGE


@dataclass
class WordTimestamp:
    word: str
    start: float
    end: float


@dataclass
class WhisperSegment:
    text: str
    start: float
    end: float
    words: list[WordTimestamp] = field(default_factory=list)


class WhisperService:
    def __init__(self, model_size: str = "", device: str = "") -> None:
        size = model_size or WHISPER_MODEL_SIZE
        dev = device or WHISPER_DEVICE
        self._model = whisper.load_model(size, device=dev)

    def transcribe(self, audio_path: str) -> list[WhisperSegment]:
        result = self._model.transcribe(
            audio_path,
            word_timestamps=True,
            language=WHISPER_LANGUAGE,
            verbose=False,
        )

        segments: list[WhisperSegment] = []
        for seg in result.get("segments", []):
            words: list[WordTimestamp] = []
            for w in seg.get("words", []):
                words.append(WordTimestamp(
                    word=w.get("word", "").strip(),
                    start=w.get("start", 0.0),
                    end=w.get("end", 0.0),
                ))
            text = seg.get("text", "").strip()
            if text or words:
                segments.append(WhisperSegment(
                    text=text,
                    start=seg.get("start", 0.0),
                    end=seg.get("end", 0.0),
                    words=words,
                ))
        return segments
