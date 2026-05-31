from __future__ import annotations

import re
import string


# Characters to strip during normalization
_PUNCTUATION = (
    string.punctuation
    + string.whitespace
    + "　、。，．《》「」！？"
    + "：；（）“”‘’【】"
)


def split_sentences(text: str) -> list[str]:
    """Split Chinese text into sentences by punctuation marks and newlines."""
    pattern = r"(?<=[。！？\n.!?;])\s*"
    raw = re.split(pattern, text)
    result: list[str] = []
    for s in raw:
        s = s.strip()
        if s:
            result.append(s)
    return result


def normalize_text(text: str) -> str:
    """Remove punctuation and collapse whitespace for alignment comparison."""
    result: list[str] = []
    for ch in text:
        if ch not in _PUNCTUATION:
            result.append(ch)
    return "".join(result)


def chars_with_positions(text: str) -> list[tuple[int, str]]:
    """Return list of (original_position, char) for meaningful chars in text."""
    result: list[tuple[int, str]] = []
    for i, ch in enumerate(text):
        if ch not in _PUNCTUATION:
            result.append((i, ch))
    return result
