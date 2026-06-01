from __future__ import annotations

import asyncio
from deep_translator import GoogleTranslator


class TranslationService:
    def __init__(self, source: str = "zh-CN", target: str = "en") -> None:
        self.source = source
        self.target = target

    def translate_batch(self, texts: list[str]) -> list[str]:
        """Translate a batch of text strings. Runs in a thread pool."""
        results: list[str] = []
        for text in texts:
            text = text.strip()
            if not text:
                results.append("")
                continue
            try:
                translated = GoogleTranslator(
                    source=self.source, target=self.target
                ).translate(text)
                results.append(translated or text)
            except Exception:
                results.append("")
        return results

    async def translate_batch_async(self, texts: list[str]) -> list[str]:
        return await asyncio.to_thread(self.translate_batch, texts)
