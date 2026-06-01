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
        self._model_size = model_size or WHISPER_MODEL_SIZE
        self._default_device = device or WHISPER_DEVICE
        self._models: dict[tuple[str, str], whisper.Whisper] = {}
        # Preload default
        self._get_model(self._default_device)

    def _get_model(self, device: str) -> whisper.Whisper:
        """Get or load a model for the given device, reusing cached instances."""
        key = (self._model_size, device)
        if key not in self._models:
            print(f"Loading Whisper model ({self._model_size}) on {device}...")
            self._models[key] = whisper.load_model(self._model_size, device=device)
        return self._models[key]

    def transcribe(self, audio_path: str, use_gpu: bool = False) -> list[WhisperSegment]:
        device = "cuda" if use_gpu else self._default_device
        model = self._get_model(device)

        result = model.transcribe(
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
