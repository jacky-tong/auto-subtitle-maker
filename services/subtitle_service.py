from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class SubtitleEntry:
    text: str
    start: float
    end: float
    text_en: str = ""


class SubtitleService:
    MAX_CHARS_PER_LINE: int = 22
    HARD_LIMIT: int = 30

    @staticmethod
    def build_srt(entries: list[SubtitleEntry], bilingual: bool = False) -> str:
        """Convert subtitle entries to SRT format string."""
        lines: list[str] = []
        index = 1
        for entry in entries:
            # Build display text — bilingual gets both languages
            if bilingual and entry.text_en:
                display_text = f"{entry.text}\n{entry.text_en}"
            else:
                display_text = entry.text

            chunks = SubtitleService._split_long_line(display_text, entry.start, entry.end)
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
        """Split a long line at natural word boundaries. Never breaks inside a Latin word."""
        text = text.strip()
        if not text:
            return []

        # For bilingual: count only the longest line
        effective_len = max(len(ln) for ln in text.split("\n")) if "\n" in text else len(text)

        if effective_len <= SubtitleService.MAX_CHARS_PER_LINE:
            return [SubtitleEntry(text=text, start=start, end=end)]

        # For bilingual, split each line independently then merge
        if "\n" in text:
            zh_line, en_line = text.split("\n", 1)
            zh_chunks = SubtitleService._split_single_line(zh_line, start, end, len(text))
            en_chunks = SubtitleService._split_single_line(en_line, start, end, len(text))
            # Merge: take max chunk count, match them up
            max_chunks = max(len(zh_chunks), len(en_chunks))
            result: list[SubtitleEntry] = []
            for i in range(max_chunks):
                zh = zh_chunks[i].text if i < len(zh_chunks) else ""
                en = en_chunks[i].text if i < len(en_chunks) else ""
                st = zh_chunks[i].start if i < len(zh_chunks) else en_chunks[i].start
                ed = zh_chunks[i].end if i < len(zh_chunks) else en_chunks[i].end
                combined = f"{zh}\n{en}".strip()
                result.append(SubtitleEntry(text=combined, start=st, end=ed))
            return result

        return SubtitleService._split_single_line(text, start, end, len(text))

    @staticmethod
    def _split_single_line(
        text: str, start: float, end: float, total_len: int
    ) -> list[SubtitleEntry]:
        """Split a single-language line."""
        text = text.strip()
        if not text:
            return []

        if len(text) <= SubtitleService.MAX_CHARS_PER_LINE:
            return [SubtitleEntry(text=text, start=start, end=end)]

        duration = end - start
        tlen = max(total_len, 1)
        chunks: list[SubtitleEntry] = []
        remaining = text
        offset = 0.0

        while remaining:
            split_at = SubtitleService._find_split_point(remaining)
            chunk_text = remaining[:split_at].strip()
            remaining = remaining[split_at:].strip()

            ratio = len(chunk_text) / tlen
            chunk_dur = duration * ratio

            chunks.append(SubtitleEntry(
                text=chunk_text,
                start=start + offset,
                end=start + offset + chunk_dur,
            ))
            offset += chunk_dur

        return chunks

    @staticmethod
    def _find_split_point(text: str) -> int:
        """Find the best position to split, respecting word boundaries."""
        if len(text) <= SubtitleService.MAX_CHARS_PER_LINE:
            return len(text)

        best = SubtitleService.MAX_CHARS_PER_LINE
        min_search = max(1, SubtitleService.MAX_CHARS_PER_LINE // 2)

        # 1. Strong punctuation
        for pos in range(best, min_search - 1, -1):
            if pos < len(text) and text[pos - 1] in '。！？；\n':
                return pos

        # 2. Soft punctuation
        for pos in range(best, min_search - 1, -1):
            if pos < len(text) and text[pos - 1] in '.!?;，,、…—-':
                return pos

        # 3. Space
        for pos in range(best, min_search - 1, -1):
            if pos < len(text) and text[pos - 1] in ' \t':
                return pos

        # 4. Scan forward for any break
        for pos in range(best + 1, min(len(text), SubtitleService.HARD_LIMIT)):
            if text[pos - 1] in '。！？；\n.!?;，,、…—- \t':
                return pos

        # 5. Safe boundary at HARD_LIMIT
        for pos in range(SubtitleService.HARD_LIMIT, min_search, -1):
            if SubtitleService._safe_boundary(text, pos):
                return pos

        # 6. Any boundary
        for pos in range(SubtitleService.HARD_LIMIT, min_search, -1):
            if SubtitleService._any_boundary(text, pos):
                return pos

        return SubtitleService.HARD_LIMIT

    @staticmethod
    def _safe_boundary(text: str, pos: int) -> bool:
        if pos <= 0 or pos >= len(text):
            return True
        p, n = text[pos - 1], text[pos]
        if re.match(r'[a-zA-Z]', p) and re.match(r'[a-zA-Z]', n):
            return False
        return True

    @staticmethod
    def _any_boundary(text: str, pos: int) -> bool:
        if pos <= 0 or pos >= len(text):
            return True
        p, n = text[pos - 1], text[pos]
        if re.match(r'[a-zA-Z]', p) and re.match(r'[a-zA-Z]', n):
            return False
        if re.match(r'[0-9]', p) and re.match(r'[0-9]', n):
            return False
        return True

    @staticmethod
    def _fmt_time(seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
