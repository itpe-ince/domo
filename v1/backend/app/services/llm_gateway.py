"""LLM Gateway client — C-1 ai-artist-interview-generation.

Wraps the tuzigroup LLM inference gateway (OpenAI-compatible /chat/completions).
Falls back to Mock mode when LLM_GATEWAY_API_KEY is not set (dev/CI friendly).

Security notes:
  - API key is read from settings (env var), never hard-coded.
  - Frontend must NEVER call this service directly; backend is the only caller.
"""
from __future__ import annotations

import logging

import httpx

from app.core.config import get_settings

log = logging.getLogger(__name__)

_MOCK_BODY = """## 작가 인터뷰 (자동 생성 / Mock 모드)

**Q. 작품 활동을 시작하게 된 계기는 무엇인가요?**

어릴 때부터 색과 형태에 매료되어 있었습니다. 처음에는 취미로 시작했지만, 점점 더 많은 시간을 작업실에서 보내게 되었습니다.

**Q. 현재 주로 어떤 매체와 장르를 다루고 있나요?**

회화를 중심으로 다양한 매체를 탐구하고 있습니다. 디지털과 아날로그를 오가며 경계를 실험하는 것을 즐깁니다.

**Q. 앞으로의 작품 계획이 있다면 공유해 주세요.**

더 많은 국제 전시에 참여하고, 작가로서의 목소리를 넓혀 가고 싶습니다. 관람객과의 소통이 제 작업의 가장 큰 동력입니다.

---
*이 인터뷰는 Domo AI 인터뷰 생성 시스템의 Mock 모드로 생성된 플레이스홀더입니다.*
"""


class LLMGatewayClient:
    """OpenAI-compatible LLM Gateway client.

    Usage:
        client = LLMGatewayClient()
        result = await client.generate_interview(prompt)
        # result = {"content": str, "model": str, "usage_tokens": int}
    """

    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = settings.llm_gateway_url.rstrip("/")
        self.api_key = settings.llm_gateway_api_key
        self.model = settings.llm_model_name

    @property
    def is_mock(self) -> bool:
        """True when API key is not configured — enables Mock mode."""
        return not bool(self.api_key)

    async def generate_interview(
        self,
        prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> dict:
        """Generate an artist interview article.

        Returns dict with keys:
          content       str  — markdown interview body
          model         str  — model identifier used
          usage_tokens  int  — total tokens consumed (0 in mock mode)
        """
        if self.is_mock:
            log.info("LLMGatewayClient: Mock mode (LLM_GATEWAY_API_KEY not set)")
            return self._mock_response(prompt)

        system_prompt = (
            "You are a professional art critic writing authentic, compelling artist "
            "interviews in Korean. Your interviews illuminate the artist's creative "
            "journey, inspirations, and vision. Write in an engaging Q&A format using "
            "markdown headers. Keep answers authentic — avoid marketing language. "
            "Each response should be 400-800 words in Korean."
        )

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt},
                        ],
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                    },
                )
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                used_model = data.get("model", self.model)
                usage_tokens = data.get("usage", {}).get("total_tokens", 0)

                log.info(
                    "LLMGatewayClient: generated interview model=%s tokens=%s",
                    used_model,
                    usage_tokens,
                )
                return {
                    "content": content,
                    "model": used_model,
                    "usage_tokens": usage_tokens,
                }

            except httpx.HTTPStatusError as exc:
                log.error(
                    "LLMGatewayClient: HTTP error %s — %s",
                    exc.response.status_code,
                    exc.response.text[:200],
                )
                raise
            except httpx.RequestError as exc:
                log.error("LLMGatewayClient: request error — %s", exc)
                raise

    async def translate_text(
        self,
        text: str,
        source_locale: str,
        target_locale: str,
    ) -> str:
        """Translate text from source_locale to target_locale via LLM Gateway.

        Mock mode fallback: returns "[MOCK {target_locale}] {text[:80]}..." so
        tests and CI pass without a real API key.

        Args:
            text: Source text (may contain markdown).
            source_locale: ISO locale code of the input, e.g. "ko".
            target_locale: ISO locale code of the desired output, e.g. "en".

        Returns:
            Translated text as a string (preserves markdown formatting).
        """
        if self.is_mock:
            log.info(
                "LLMGatewayClient.translate_text: Mock mode %s→%s",
                source_locale,
                target_locale,
            )
            preview = text[:80].replace("\n", " ")
            return f"[MOCK {target_locale}] {preview}"

        locale_names = {
            "ko": "Korean",
            "en": "English",
            "ja": "Japanese",
            "zh": "Chinese (Simplified)",
            "es": "Spanish",
        }
        src_name = locale_names.get(source_locale, source_locale)
        tgt_name = locale_names.get(target_locale, target_locale)

        prompt = (
            f"Translate the following text from {src_name} to {tgt_name}. "
            "Preserve all markdown formatting (headers, bold, lists, etc.). "
            "Output only the translated text — no explanation, no code block wrapper.\n\n"
            f"{text}"
        )
        result = await self.generate_interview(prompt, max_tokens=2000, temperature=0.3)
        return result["content"]

    def _mock_response(self, _prompt: str) -> dict:
        return {
            "content": _MOCK_BODY,
            "model": "mock-gateway",
            "usage_tokens": 0,
        }
