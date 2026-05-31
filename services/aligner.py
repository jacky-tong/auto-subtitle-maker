from __future__ import annotations

from dataclasses import dataclass

from services.whisper_service import WhisperSegment, WordTimestamp
from utils.text_utils import normalize_text


@dataclass
class AlignedSentence:
    text: str
    start: float
    end: float
    confidence: float


class ForcedAligner:
    MATCH_SCORE: int = 2
    MISMATCH_SCORE: int = -1
    GAP_SCORE: int = -1

    def align(
        self,
        doc_sentences: list[str],
        whisper_segments: list[WhisperSegment],
    ) -> list[AlignedSentence]:
        """Align document sentences to Whisper-derived timestamps.

        Uses Smith-Waterman local alignment at character level, then maps
        document sentences to time ranges through the alignment path.
        """
        # 1. Build flat character arrays
        doc_chars, doc_positions = self._build_char_array(doc_sentences)
        whisper_chars, whisper_timestamps = self._build_char_array_from_whisper(
            whisper_segments
        )

        if not doc_chars or not whisper_chars:
            return self._fallback_align(doc_sentences, whisper_segments)

        # 2. Run Smith-Waterman
        alignment = self._smith_waterman(doc_chars, whisper_chars)

        # 3. Map sentences through alignment to timestamps
        return self._map_sentences_to_time(
            doc_sentences, doc_positions, whisper_timestamps, alignment
        )

    def _build_char_array(
        self, sentences: list[str]
    ) -> tuple[list[str], list[list[int]]]:
        """Build flat char array from document sentences.

        Returns:
            chars: list of normalized characters
            sentence_boundaries: for each char index, which sentence it belongs to
        """
        chars: list[str] = []
        boundaries: list[int] = []
        for sent_idx, sent in enumerate(sentences):
            norm = normalize_text(sent)
            for ch in norm:
                chars.append(ch)
                boundaries.append(sent_idx)
        return chars, boundaries

    def _build_char_array_from_whisper(
        self, segments: list[WhisperSegment]
    ) -> tuple[list[str], list[tuple[float, float]]]:
        """Build flat char array from Whisper word timestamps.

        Returns:
            chars: normalized characters from Whisper output
            timestamps: (start, end) for each character
        """
        chars: list[str] = []
        timestamps: list[tuple[float, float]] = []
        for seg in segments:
            if seg.words:
                for w in seg.words:
                    norm = normalize_text(w.word)
                    if norm:
                        n = len(norm)
                        char_dur = (w.end - w.start) / n if n > 0 else 0.0
                        for j, ch in enumerate(norm):
                            chars.append(ch)
                            ts = w.start + j * char_dur
                            te = ts + char_dur
                            timestamps.append((ts, te))
            else:
                norm = normalize_text(seg.text)
                if norm:
                    n = len(norm)
                    char_dur = (seg.end - seg.start) / n if n > 0 else 0.1
                    for j, ch in enumerate(norm):
                        chars.append(ch)
                        ts = seg.start + j * char_dur
                        te = ts + char_dur
                        timestamps.append((ts, te))
        return chars, timestamps

    def _smith_waterman(
        self, doc_chars: list[str], whisper_chars: list[str]
    ) -> list[tuple[int, int]]:
        """Smith-Waterman local alignment between document and Whisper chars.

        Returns list of (doc_idx, whisper_idx) aligned pairs.
        """
        n, m = len(doc_chars) + 1, len(whisper_chars) + 1
        # Initialize matrix
        matrix = [[0] * m for _ in range(n)]
        traceback = [[0] * m for _ in range(n)]
        # 0=stop, 1=diag, 2=up, 3=left

        max_score = 0
        max_pos = (0, 0)

        for i in range(1, n):
            for j in range(1, m):
                match = matrix[i - 1][j - 1] + (
                    self.MATCH_SCORE if doc_chars[i - 1] == whisper_chars[j - 1]
                    else self.MISMATCH_SCORE
                )
                delete = matrix[i - 1][j] + self.GAP_SCORE
                insert = matrix[i][j - 1] + self.GAP_SCORE

                if match >= delete and match >= insert and match > 0:
                    matrix[i][j] = match
                    traceback[i][j] = 1
                elif delete >= insert and delete > 0:
                    matrix[i][j] = delete
                    traceback[i][j] = 2
                elif insert > 0:
                    matrix[i][j] = insert
                    traceback[i][j] = 3
                else:
                    matrix[i][j] = 0
                    traceback[i][j] = 0

                if matrix[i][j] > max_score:
                    max_score = matrix[i][j]
                    max_pos = (i, j)

        # Traceback from max score position
        alignment: list[tuple[int, int]] = []
        i, j = max_pos
        while i > 0 and j > 0 and matrix[i][j] > 0:
            direction = traceback[i][j]
            if direction == 1:  # diagonal
                alignment.append((i - 1, j - 1))
                i -= 1
                j -= 1
            elif direction == 2:  # up (gap in whisper)
                i -= 1
            elif direction == 3:  # left (gap in doc)
                j -= 1
            else:
                break

        alignment.reverse()
        return alignment

    def _map_sentences_to_time(
        self,
        sentences: list[str],
        doc_boundaries: list[int],
        whisper_timestamps: list[tuple[float, float]],
        alignment: list[tuple[int, int]],
    ) -> list[AlignedSentence]:
        """Map document sentences to timestamps via the alignment path."""
        # For each sentence, collect all aligned whisper time ranges
        sent_times: dict[int, list[tuple[float, float]]] = {i: [] for i in range(len(sentences))}
        sent_match_count: dict[int, int] = {i: 0 for i in range(len(sentences))}
        sent_total_chars: dict[int, int] = {i: 0 for i in range(len(sentences))}

        for di in range(len(doc_boundaries)):
            sent_idx = doc_boundaries[di]
            sent_total_chars[sent_idx] += 1

        for doc_idx, whisper_idx in alignment:
            sent_idx = doc_boundaries[doc_idx]
            ts = whisper_timestamps[whisper_idx]
            sent_times[sent_idx].append(ts)
            sent_match_count[sent_idx] += 1

        # Build aligned sentences
        result: list[AlignedSentence] = []
        for sent_idx, sent in enumerate(sentences):
            times = sent_times[sent_idx]
            if times:
                start = min(t[0] for t in times)
                end = max(t[1] for t in times)
                total = sent_total_chars.get(sent_idx, 1) or 1
                confidence = min(sent_match_count[sent_idx] / total, 1.0)
            else:
                # Interpolate: find closest aligned sentences before/after
                start, end, confidence = self._interpolate_time(
                    sent_idx, sent_times, sentences, result
                )

            result.append(AlignedSentence(
                text=sent,
                start=start,
                end=max(end, start + 0.5),
                confidence=confidence,
            ))

        # Resolve overlaps
        result = self._resolve_overlaps(result)
        return result

    def _interpolate_time(
        self,
        sent_idx: int,
        sent_times: dict[int, list[tuple[float, float]]],
        sentences: list[str],
        existing: list[AlignedSentence],
    ) -> tuple[float, float, float]:
        """Interpolate timing for a sentence with no direct alignment."""
        # Find previous aligned sentence
        prev_end = 0.0
        for i in range(sent_idx - 1, -1, -1):
            if sent_times.get(i):
                prev_end = max(t[1] for t in sent_times[i])
                break
            elif i < len(existing):
                prev_end = existing[i].end
                break

        # Find next aligned sentence
        next_start = prev_end + len(sentences[sent_idx]) * 0.3
        for i in range(sent_idx + 1, len(sentences)):
            if sent_times.get(i):
                next_start = min(t[0] for t in sent_times[i])
                break

        # If still no next, estimate based on character count
        if next_start <= prev_end:
            char_count = len(sentences[sent_idx].strip())
            next_start = prev_end + max(char_count * 0.15, 1.0)

        duration = next_start - prev_end
        start = prev_end + duration * 0.1
        end = next_start - duration * 0.1

        if end <= start:
            end = start + 0.5

        return start, end, 0.3

    def _resolve_overlaps(
        self, entries: list[AlignedSentence]
    ) -> list[AlignedSentence]:
        """Ensure no overlapping time ranges between consecutive entries."""
        for i in range(len(entries) - 1):
            if entries[i].end > entries[i + 1].start:
                mid = (entries[i].end + entries[i + 1].start) / 2
                entries[i].end = mid - 0.05
                entries[i + 1].start = mid + 0.05
        return entries

    def _fallback_align(
        self,
        doc_sentences: list[str],
        whisper_segments: list[WhisperSegment],
    ) -> list[AlignedSentence]:
        """Fallback: distribute sentences evenly across available time."""
        if not whisper_segments:
            return [
                AlignedSentence(text=s, start=0.0, end=1.0, confidence=0.0)
                for s in doc_sentences
            ]

        total_start = whisper_segments[0].start
        total_end = whisper_segments[-1].end
        total_duration = total_end - total_start
        total_chars = sum(len(normalize_text(s)) for s in doc_sentences) or 1

        result: list[AlignedSentence] = []
        current_time = total_start

        for sent in doc_sentences:
            char_count = len(normalize_text(sent))
            duration = (char_count / total_chars) * total_duration
            result.append(AlignedSentence(
                text=sent,
                start=current_time,
                end=current_time + duration,
                confidence=0.2,
            ))
            current_time += duration

        return result
