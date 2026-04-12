"""Email provider interface (Phase 4 M5 / shared with M1).

Reference: phase4.design.md §8
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class EmailMessage:
    to: str
    subject: str
    html: str
    text: str | None = None
    tags: list[str] | None = None


class EmailProvider(ABC):
    """Abstract email provider — mock, Resend, SES, etc."""

    name: str

    @abstractmethod
    async def send(self, message: EmailMessage) -> str:
        """Send an email and return the provider message id."""
