"""Shipping tracking with adapter pattern.

Providers:
  - mock: Development (instant status updates)
  - aftership: Aftership API (900+ carriers, global)

Usage:
  provider = get_shipping_provider()
  status = await provider.track("TRACKING123")
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.core.config import get_settings

log = logging.getLogger(__name__)


@dataclass
class ShippingStatus:
    tracking_number: str
    carrier: str
    status: str  # pending | in_transit | delivered | exception
    last_update: str | None = None
    location: str | None = None
    estimated_delivery: str | None = None


class ShippingProvider(ABC):
    @abstractmethod
    async def track(self, tracking_number: str, carrier: str = "") -> ShippingStatus:
        ...

    @abstractmethod
    async def get_carriers(self) -> list[dict]:
        ...


class MockShippingProvider(ShippingProvider):
    async def track(self, tracking_number: str, carrier: str = "") -> ShippingStatus:
        return ShippingStatus(
            tracking_number=tracking_number,
            carrier=carrier or "mock_carrier",
            status="in_transit",
            last_update="Mock: package is on its way",
            location="Seoul Distribution Center",
            estimated_delivery="2~3 business days",
        )

    async def get_carriers(self) -> list[dict]:
        return [
            {"code": "cj", "name": "CJ대한통운"},
            {"code": "hanjin", "name": "한진택배"},
            {"code": "lotte", "name": "롯데택배"},
            {"code": "fedex", "name": "FedEx"},
            {"code": "dhl", "name": "DHL"},
            {"code": "ups", "name": "UPS"},
        ]


class AftershippProvider(ShippingProvider):
    """Aftership API — placeholder."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def track(self, tracking_number: str, carrier: str = "") -> ShippingStatus:
        raise NotImplementedError("Aftership integration pending")

    async def get_carriers(self) -> list[dict]:
        raise NotImplementedError("Aftership integration pending")


def get_shipping_provider() -> ShippingProvider:
    settings = get_settings()
    provider = getattr(settings, "shipping_provider", "mock")
    if provider == "aftership":
        return AftershippProvider(api_key=getattr(settings, "aftership_api_key", ""))
    return MockShippingProvider()
