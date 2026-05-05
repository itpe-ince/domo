"""Simple server-side i18n helper for push notification strings (D-5 carry-over).

Uses a static dict lookup keyed by (notification_key, locale).
Fallback: unknown locale or missing key falls back to "ko".

Supported locales: ko, en, ja, zh, es
Supported notification keys: auction_ending_24h, auction_ending_6h,
                              auction_ending_1h, auction_ended
"""
from __future__ import annotations

# ─── Translation table ───────────────────────────────────────────────────────
# Structure: {notification_key: {"title": {locale: str}, "body": {locale: str}}}

_TRANSLATIONS: dict[str, dict[str, dict[str, str]]] = {
    "auction_ending_24h": {
        "title": {
            "ko": "경매 종료 24시간 전",
            "en": "Auction ending in 24h",
            "ja": "オークション終了24時間前",
            "zh": "拍卖结束24小时前",
            "es": "Subasta termina en 24h",
        },
        "body": {
            "ko": "경매가 24시간 후에 종료됩니다. 지금 확인해보세요.",
            "en": "The auction ends in 24 hours. Check it out now.",
            "ja": "オークションは24時間後に終了します。今すぐ確認してください。",
            "zh": "拍卖将在24小时后结束。现在去看看吧。",
            "es": "La subasta termina en 24 horas. ¡Compruébalo ahora!",
        },
    },
    "auction_ending_6h": {
        "title": {
            "ko": "경매 종료 6시간 전",
            "en": "Auction ending in 6h",
            "ja": "オークション終了6時間前",
            "zh": "拍卖结束6小时前",
            "es": "Subasta termina en 6h",
        },
        "body": {
            "ko": "경매가 6시간 후에 종료됩니다. 마지막 입찰 기회를 놓치지 마세요.",
            "en": "The auction ends in 6 hours. Don't miss your last chance to bid.",
            "ja": "オークションは6時間後に終了します。最後の入札チャンスをお見逃しなく。",
            "zh": "拍卖将在6小时后结束。不要错过最后的出价机会。",
            "es": "La subasta termina en 6 horas. No pierdas tu última oportunidad de pujar.",
        },
    },
    "auction_ending_1h": {
        "title": {
            "ko": "경매 종료 1시간 전",
            "en": "Auction ending in 1h",
            "ja": "オークション終了1時間前",
            "zh": "拍卖结束1小时前",
            "es": "Subasta termina en 1h",
        },
        "body": {
            "ko": "경매가 1시간 후에 종료됩니다! 서두르세요.",
            "en": "The auction ends in 1 hour! Hurry up.",
            "ja": "オークションは1時間後に終了します！急いでください。",
            "zh": "拍卖将在1小时后结束！快点吧。",
            "es": "¡La subasta termina en 1 hora! Date prisa.",
        },
    },
    "auction_ended": {
        "title": {
            "ko": "경매가 종료되었습니다",
            "en": "Auction has ended",
            "ja": "オークションが終了しました",
            "zh": "拍卖已结束",
            "es": "La subasta ha finalizado",
        },
        "body": {
            "ko": "경매가 종료되었습니다. 결과를 확인해보세요.",
            "en": "The auction has ended. Check the results.",
            "ja": "オークションが終了しました。結果を確認してください。",
            "zh": "拍卖已结束。查看结果。",
            "es": "La subasta ha finalizado. Consulta los resultados.",
        },
    },
}

_SUPPORTED_LOCALES: frozenset[str] = frozenset({"ko", "en", "ja", "zh", "es"})
_FALLBACK_LOCALE = "ko"


def t(key: str, field: str, lang: str | None, fallback: str = _FALLBACK_LOCALE) -> str:
    """Return translated string for *key* + *field* in *lang*.

    Args:
        key:      Notification key, e.g. "auction_ending_24h".
        field:    "title" or "body".
        lang:     Locale string from user.language (e.g. "en"). None → fallback.
        fallback: Locale to use when *lang* is None or unsupported. Default "ko".

    Returns:
        Translated string, or fallback-locale string, or key+field as last resort.
    """
    resolved_lang = lang if (lang and lang in _SUPPORTED_LOCALES) else fallback
    translations = _TRANSLATIONS.get(key, {})
    field_map = translations.get(field, {})
    return field_map.get(resolved_lang) or field_map.get(fallback) or f"{key}.{field}"
