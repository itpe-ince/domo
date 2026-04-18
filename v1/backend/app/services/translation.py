"""Translation service with adapter pattern.

Providers:
  - mock: Returns "[EN] {text}" for development
  - google: Google Cloud Translation API v2
  - deepl: DeepL API (future)

Usage:
  provider = get_translation_provider()
  translated = await provider.translate("안녕하세요", target_lang="en")
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod

import httpx

from app.core.config import get_settings

log = logging.getLogger(__name__)


class TranslationProvider(ABC):
    @abstractmethod
    async def translate(self, text: str, target_lang: str, source_lang: str | None = None) -> str:
        ...

    async def translate_batch(self, texts: list[str], target_lang: str, source_lang: str | None = None) -> list[str]:
        """Translate multiple texts. Default: sequential calls."""
        return [await self.translate(t, target_lang, source_lang) for t in texts]


class OllamaTranslationProvider(TranslationProvider):
    """Local AI translation via Ollama (gemma3, qwen3-vl, etc.)."""

    def __init__(self, model: str = "gemma3:4b", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url

    async def translate(self, text: str, target_lang: str, source_lang: str | None = None) -> str:
        if not text or len(text.strip()) == 0:
            return text

        lang_names = {
            "ko": "Korean", "en": "English", "ja": "Japanese",
            "zh": "Chinese", "es": "Spanish", "fr": "French",
            "de": "German", "it": "Italian",
        }
        target_name = lang_names.get(target_lang, target_lang)
        source_name = lang_names.get(source_lang, "auto-detect") if source_lang else "auto-detect"

        prompt = (
            f"Translate the following text to {target_name}. "
            f"Only return the translated text, nothing else. "
            f"Do not add quotes or explanations.\n\n{text}"
        )

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.1},
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                result = data.get("response", "").strip()
                # Clean up: remove surrounding quotes if present
                if result.startswith('"') and result.endswith('"'):
                    result = result[1:-1]
                return result or text
        except Exception as e:
            log.warning("Ollama translation failed: %s", e)
            return text

    async def translate_batch(self, texts: list[str], target_lang: str, source_lang: str | None = None) -> list[str]:
        # Ollama doesn't support batch natively, use sequential
        return [await self.translate(t, target_lang, source_lang) for t in texts]


class MockTranslationProvider(TranslationProvider):
    """Development mock — prefixes text with language tag."""

    async def translate(self, text: str, target_lang: str, source_lang: str | None = None) -> str:
        if not text:
            return text
        tag = target_lang.upper()
        return f"[{tag}] {text}"


class GoogleTranslationProvider(TranslationProvider):
    """Google Cloud Translation API v2."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.endpoint = "https://translation.googleapis.com/language/translate/v2"

    async def translate(self, text: str, target_lang: str, source_lang: str | None = None) -> str:
        if not text:
            return text
        async with httpx.AsyncClient(timeout=10.0) as client:
            params = {
                "q": text,
                "target": target_lang,
                "key": self.api_key,
                "format": "text",
            }
            if source_lang:
                params["source"] = source_lang
            resp = await client.post(self.endpoint, data=params)
            resp.raise_for_status()
            data = resp.json()
            translations = data.get("data", {}).get("translations", [])
            if translations:
                return translations[0].get("translatedText", text)
            return text

    async def translate_batch(self, texts: list[str], target_lang: str, source_lang: str | None = None) -> list[str]:
        if not texts:
            return []
        async with httpx.AsyncClient(timeout=15.0) as client:
            params: dict = {
                "target": target_lang,
                "key": self.api_key,
                "format": "text",
            }
            if source_lang:
                params["source"] = source_lang
            # Google API supports multiple q params
            params_list = [(k, v) for k, v in params.items()] + [("q", t) for t in texts]
            resp = await client.post(self.endpoint, data=params_list)
            resp.raise_for_status()
            data = resp.json()
            translations = data.get("data", {}).get("translations", [])
            return [t.get("translatedText", texts[i]) for i, t in enumerate(translations)]


def get_translation_provider(override: dict | None = None) -> TranslationProvider:
    """Get translation provider. Uses override dict or falls back to env config.

    override comes from system_settings.translation (admin-configurable at runtime).
    """
    config = override or {}
    provider_name = config.get("provider") or getattr(get_settings(), "translation_provider", "auto")
    google_key = config.get("google_api_key") or getattr(get_settings(), "google_translate_api_key", "")
    ollama_url = config.get("ollama_url") or getattr(get_settings(), "ollama_url", "http://100.75.139.86:11434")
    ollama_model = config.get("ollama_model") or getattr(get_settings(), "ollama_translation_model", "gemma4:latest")

    if provider_name == "google" and google_key:
        return GoogleTranslationProvider(google_key)
    elif provider_name == "ollama":
        return OllamaTranslationProvider(model=ollama_model, base_url=ollama_url)
    elif provider_name == "auto":
        if google_key:
            return GoogleTranslationProvider(google_key)
        return OllamaTranslationProvider(model=ollama_model, base_url=ollama_url)
    elif provider_name == "mock":
        return MockTranslationProvider()
    else:
        return OllamaTranslationProvider(model=ollama_model, base_url=ollama_url)


async def get_translation_provider_from_db(db) -> TranslationProvider:
    """Load translation settings from system_settings (admin-configurable)."""
    from app.services.settings import get_setting
    config = await get_setting(db, "translation")
    return get_translation_provider(config)
