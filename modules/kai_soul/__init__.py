"""KAI-SOUL: Serce partnerstwa AI-Człowiek dla Kai256."""

from modules.kai_soul.types import UserMode

__all__ = ["KAISoul", "UserMode"]


def __getattr__(name: str):
    if name == "KAISoul":
        from modules.kai_soul.core import KAISoul

        return KAISoul
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
