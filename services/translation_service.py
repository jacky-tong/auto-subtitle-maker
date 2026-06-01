from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from deep_translator import MyMemoryTranslator


class TranslationService:
    def __init__(self, source: str = "zh-CN", target: str = "en-GB") -> None:
        self.source = source
        self.target = target

    def translate_batch(self, texts: list[str]) -> list[str]:
        """Translate texts using MyMemory (free, no API key, works in China)."""
        if not texts:
            return []

        non_empty = [(i, t.strip()) for i, t in enumerate(texts) if t.strip()]
        if not non_empty:
            return [""] * len(texts)

        results: list[str] = [""] * len(texts)
        errors = 0

        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = {}
            for idx, text in non_empty:
                f = pool.submit(self._translate_one, text)
                futures[f] = idx

            for future in as_completed(futures):
                idx = futures[future]
                try:
                    translated = future.result()
                    if translated:
                        results[idx] = translated
                    else:
                        errors += 1
                except Exception:
                    errors += 1

        if errors > 0:
            print(f"[Translation] {errors}/{len(non_empty)} entries failed")

        return results

    def _translate_one(self, text: str) -> str:
        """Translate a single text via MyMemory."""
        try:
            translated = MyMemoryTranslator(
                source=self.source, target=self.target
            ).translate(text)
            return translated or text
        except Exception:
            return ""

    async def translate_batch_async(self, texts: list[str]) -> list[str]:
        return await asyncio.to_thread(self.translate_batch, texts)
