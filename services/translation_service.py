from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from deep_translator import GoogleTranslator


class TranslationService:
    def __init__(self, source: str = "zh-CN", target: str = "en") -> None:
        self.source = source
        self.target = target

    @staticmethod
    def _translate_one(args: tuple[int, str, str, str]) -> tuple[int, str]:
        """Translate a single text. Returns (index, translated_text)."""
        idx, text, source, target = args
        text = text.strip()
        if not text:
            return idx, ""
        try:
            translated = GoogleTranslator(source=source, target=target).translate(text)
            return idx, translated or text
        except Exception:
            return idx, ""

    def translate_batch(self, texts: list[str]) -> list[str]:
        """Translate texts using parallel requests (8 concurrent workers).

        Much faster than sequential — 50 entries complete in ~6 requests worth of latency.
        """
        if not texts:
            return []

        results: list[str] = [""] * len(texts)
        tasks = [(i, t, self.source, self.target) for i, t in enumerate(texts) if t.strip()]

        if not tasks:
            return results

        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = {pool.submit(self._translate_one, t): t for t in tasks}
            for future in as_completed(futures):
                idx, translated = future.result()
                results[idx] = translated

        return results

    async def translate_batch_async(self, texts: list[str]) -> list[str]:
        return await asyncio.to_thread(self.translate_batch, texts)
