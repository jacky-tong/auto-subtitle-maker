from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class SubtitleEntry:
    text: str
    start: float
    end: float


class SubtitleService:
    # Soft limit — splitter will look for a natural break near this length
    MAX_CHARS_PER_LINE: int = 22
    # Hard limit — if no natural break found, force split here
    HARD_LIMIT: int = 30

    # Characters that make good split points (ordered by preference)
    SPLIT_CHARS = r'[。！？；\n.!?;，,、\s—…\-—]'

    @staticmethod
    def build_srt(entries: list[SubtitleEntry]) -> str:
        """Convert subtitle entries to SRT format string, splitting long lines."""
        lines: list[str] = []
        index = 1
        for entry in entries:
            chunks = SubtitleService._split_long_line(entry.text, entry.start, entry.end)
            for chunk in chunks:
                lines.append(str(index))
                lines.append(
                    f"{SubtitleService._fmt_time(chunk.start)} --> "
                    f"{SubtitleService._fmt_time(chunk.end)}"
                )
                lines.append(chunk.text)
                lines.append("")
                index += 1
        return "\n".join(lines)

    @staticmethod
    def _split_long_line(
        text: str, start: float, end: float
    ) -> list[SubtitleEntry]:
        """Split a long subtitle line at natural word boundaries.

        Prioritises: punctuation > space > word boundary.
        Never breaks inside a Latin word like "python".
        """
        text = text.strip()
        if not text:
            return []

        if len(text) <= SubtitleService.MAX_CHARS_PER_LINE:
            return [SubtitleEntry(text=text, start=start, end=end)]

        duration = end - start
        chunks: list[SubtitleEntry] = []
        remaining = text
        offset = 0.0

        while remaining:
            # Find the best split position
            split_at = SubtitleService._find_split_point(remaining)

            chunk_text = remaining[:split_at].strip()
            remaining = remaining[split_at:].strip()

            # Calculate proportional time for this chunk
            chunk_ratio = len(chunk_text) / len(text) if len(text) > 0 else 1.0
            chunk_duration = duration * chunk_ratio

            chunks.append(SubtitleEntry(
                text=chunk_text,
                start=start + offset,
                end=start + offset + chunk_duration,
            ))
            offset += chunk_duration

        return chunks

    @staticmethod
    def _find_split_point(text: str) -> int:
        """Find the best position to split a line, respecting word boundaries.

        Strategy:
        1. Look for a punctuation mark near MAX_CHARS_PER_LINE
        2. Look for a space near MAX_CHARS_PER_LINE
        3. Look for a Chinese character boundary near MAX_CHARS_PER_LINE
        4. Hard split at HARD_LIMIT, but only at word boundaries
        5. If word is too long (>HARD_LIMIT), force split inside it
        """
        if len(text) <= SubtitleService.MAX_CHARS_PER_LINE:
            return len(text)

        # --- Search range: from MAX_CHARS_PER_LINE down to half of it ---
        best = SubtitleService.MAX_CHARS_PER_LINE
        min_search = max(1, SubtitleService.MAX_CHARS_PER_LINE // 2)

        # 1. Punctuation: prefer sentence-ending, then clause
        for pos in range(best, min_search - 1, -1):
            if pos < len(text) and text[pos - 1] in '。！？；\n':
                return pos

        # 2. Other punctuation
        for pos in range(best, min_search - 1, -1):
            if pos < len(text) and text[pos - 1] in '.!?;，,、…—-':
                # Check not mid-word — split after punct is safe
                return pos

        # 3. Space
        for pos in range(best, min_search - 1, -1):
            if pos < len(text) and text[pos - 1] in ' \t':
                return pos

        # 4. Look further: try up to HARD_LIMIT for any split point
        for pos in range(best + 1, min(len(text), SubtitleService.HARD_LIMIT)):
            if text[pos - 1] in '。！？；\n.!?;，,、…—- \t':
                return pos

        # 5. No natural break found within HARD_LIMIT.
        #    Split at the nearest safe boundary around HARD_LIMIT.
        #    Safe = between CJK chars, or after a Latin word, or before a Latin word.
        for pos in range(SubtitleService.HARD_LIMIT, min_search, -1):
            if SubtitleService._is_safe_boundary(text, pos):
                return pos

        # 6. Last resort: find ANY safe boundary near HARD_LIMIT
        for pos in range(SubtitleService.HARD_LIMIT, min_search, -1):
            if SubtitleService._is_any_boundary(text, pos):
                return pos

        # 7. Give up — hard split at HARD_LIMIT
        return SubtitleService.HARD_LIMIT

    @staticmethod
    def _is_safe_boundary(text: str, pos: int) -> bool:
        """Return True if splitting at `pos` won't break a Latin word.

        Safe boundaries are: between two CJK chars, or at a CJK<->Latin transition.
        """
        if pos <= 0 or pos >= len(text):
            return True

        prev_char = text[pos - 1]
        next_char = text[pos]

        prev_latin = bool(re.match(r'[a-zA-Z]', prev_char))
        next_latin = bool(re.match(r'[a-zA-Z]', next_char))

        # Both Latin = inside a word → NOT safe
        if prev_latin and next_latin:
            return False

        return True

    @staticmethod
    def _is_any_boundary(text: str, pos: int) -> bool:
        """Check ANY kind of boundary (even mid-Chinese-word is OK here)."""
        if pos <= 0 or pos >= len(text):
            return True

        prev_char = text[pos - 1]
        next_char = text[pos]

        # Don't break a Latin word
        if re.match(r'[a-zA-Z]', prev_char) and re.match(r'[a-zA-Z]', next_char):
            return False

        # Don't break a digit sequence
        if re.match(r'[0-9]', prev_char) and re.match(r'[0-9]', next_char):
            return False

        return True

    @staticmethod
    def _fmt_time(seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
