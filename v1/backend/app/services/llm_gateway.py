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
from app.services.otel_setup import get_tracer

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
        tracer = get_tracer(__name__)
        with tracer.start_as_current_span("llm.generate_interview") as span:
            span.set_attribute("model", self.model)
            span.set_attribute("max_tokens", max_tokens)
            span.set_attribute("mock_mode", self.is_mock)
            result = await self._generate_interview_inner(
                prompt=prompt, max_tokens=max_tokens, temperature=temperature
            )
            span.set_attribute("usage_tokens", result.get("usage_tokens", 0))
            return result

    async def _generate_interview_inner(
        self,
        prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> dict:
        """Inner implementation — called from generate_interview with OTel span."""
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

    async def generate_artwork_caption(
        self,
        image_url: str,
        locale: str = "ko",
        max_tokens: int = 300,
    ) -> dict:
        """작품 이미지 → 캡션 생성 (vision 모델).

        K-3 ai-artwork-caption: tuzigroup LLM Gateway vision 모델 호출.

        Mock 모드 시: {"content": None, "model": "mock-gateway", "usage_tokens": 0}
        vision 미지원 시: text-only fallback (image URL만 전달) 시도.

        Returns dict:
            content: str | None — 생성된 캡션 (2~3문장), 실패 시 None
            model: str — 사용된 모델 식별자
            usage_tokens: int — 소비 토큰 수
        """
        if self.is_mock:
            log.warning(
                "[ArtworkCaption] Mock mode — LLM_GATEWAY_API_KEY 미설정. "
                "image_url=%s, content=None",
                image_url,
            )
            return {"content": None, "model": "mock-gateway", "usage_tokens": 0}

        system_prompt = (
            "당신은 전문 미술 큐레이터입니다. 작품 이미지를 보고 장르, 기법, 색채, 감정, 주제를 "
            "간결하고 명확하게 설명하는 전문가입니다."
        )
        user_prompt = (
            f"이 작품 이미지를 보고 다음 기준으로 한국어 캡션을 2~3문장으로 작성하세요.\n"
            "- 장르와 기법 (예: 수채화, 디지털 아트, 유화 등)\n"
            "- 주요 색채와 구도\n"
            "- 작품이 전달하는 감정 또는 주제\n"
            "- 마케팅 언어 사용 금지, 객관적 설명에 집중\n"
            "- 출력: 캡션 텍스트만 (설명이나 서론 없이)\n\n"
            f"[image: {image_url}]"
        )

        async with httpx.AsyncClient(timeout=10.0) as client:
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
                            {"role": "user", "content": user_prompt},
                        ],
                        "max_tokens": max_tokens,
                        "temperature": 0.5,
                    },
                )
                # vision 미지원 감지 (400 또는 415)
                if response.status_code in (400, 415):
                    raise VisionNotSupportedError(
                        f"vision not supported: {response.status_code} {response.text[:100]}"
                    )
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                used_model = data.get("model", self.model)
                usage_tokens = data.get("usage", {}).get("total_tokens", 0)

                log.info(
                    "[ArtworkCaption] vision caption generated model=%s tokens=%s",
                    used_model,
                    usage_tokens,
                )
                return {
                    "content": content,
                    "model": used_model,
                    "usage_tokens": usage_tokens,
                }

            except VisionNotSupportedError:
                raise
            except httpx.TimeoutException:
                log.warning("[ArtworkCaption] vision call timeout image_url=%s", image_url)
                return {"content": None, "model": self.model, "usage_tokens": 0}
            except httpx.HTTPStatusError as exc:
                log.error(
                    "[ArtworkCaption] HTTP error %s — %s",
                    exc.response.status_code,
                    exc.response.text[:200],
                )
                return {"content": None, "model": self.model, "usage_tokens": 0}
            except httpx.RequestError as exc:
                log.error("[ArtworkCaption] request error — %s", exc)
                return {"content": None, "model": self.model, "usage_tokens": 0}

    def _mock_response(self, _prompt: str) -> dict:
        return {
            "content": _MOCK_BODY,
            "model": "mock-gateway",
            "usage_tokens": 0,
        }


class VisionNotSupportedError(Exception):
    """vision 모델 미지원 시 발생 — text-only fallback 트리거."""
