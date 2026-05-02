from abc import ABC, abstractmethod


class BasePayer(ABC):
    """
    Abstract base for all payer adapters.
    Each payer has a different communication channel (API, portal, email, phone, physical).
    The adapter pattern normalises these into a uniform submit/poll interface
    so the agent's state machine doesn't need to know the channel details.
    """

    CHANNEL: str = "unknown"  # Overridden by subclasses

    @abstractmethod
    def submit(self, case) -> dict:
        """Submit a pre-auth request. Returns a dict with at least {'status': ...}."""
        raise NotImplementedError

    @abstractmethod
    def get_response(self, case) -> str:
        """Poll / check for a TPA response. Returns one of: APPROVED, REJECTED, QUERY, PENDING."""
        raise NotImplementedError