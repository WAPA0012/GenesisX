"""Capability tokens for tool access control."""
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel


class CapabilityToken(BaseModel):
    """A capability token grants permission to use specific tools.

    From Section 4.2 of code outline: capability management.
    """
    token_id: str
    capabilities: List[str]  # List of capability names (e.g., "llm_access", "file_system")
    ttl: Optional[int] = None  # Time-to-live in ticks (None = permanent)
    budget_cpu_tokens: int = 10000
    budget_money: float = 1.0
    revocable: bool = True
    audit_scope: str = "default"
    issued_tick: int = 0

    def is_expired(self, current_tick: int) -> bool:
        """Check if token has expired.

        Args:
            current_tick: Current tick number

        Returns:
            True if expired
        """
        if self.ttl is None:
            return False
        # TTL=10 意味着令牌有效期为10个tick（tick 0-9），在第10个tick过期
        return (current_tick - self.issued_tick) >= self.ttl

    def has_capability(self, capability: str) -> bool:
        """Check if token grants a capability.

        Args:
            capability: Capability name

        Returns:
            True if granted
        """
        return capability in self.capabilities


class CapabilityManager:
    """Manages capability tokens."""

    def __init__(self):
        """Initialize capability manager."""
        self._tokens: List[CapabilityToken] = []
        self._issue_default_tokens()

    def _issue_default_tokens(self):
        """Issue default capability tokens."""
        # Default token with basic capabilities
        default_token = CapabilityToken(
            token_id="default",
            capabilities=["llm_access", "file_system"],
            ttl=None,  # Permanent
            budget_cpu_tokens=100000,
            budget_money=10.0,
            issued_tick=0,
        )
        self._tokens.append(default_token)

    def issue_token(self, token: CapabilityToken):
        """Issue a new capability token.

        Args:
            token: Token to issue
        """
        self._tokens.append(token)

    def revoke_token(self, token_id: str):
        """Revoke a token.

        Args:
            token_id: Token ID to revoke
        """
        self._tokens = [t for t in self._tokens if t.token_id != token_id]

    def check_capability(self, capability: str, current_tick: int) -> bool:
        """Check if any active token grants a capability.

        Args:
            capability: Capability to check
            current_tick: Current tick

        Returns:
            True if capability is granted
        """
        for token in self._tokens:
            if not token.is_expired(current_tick):
                if token.has_capability(capability):
                    return True
        return False

    def get_active_capabilities(self, current_tick: int) -> List[str]:
        """Get list of all active capabilities.

        Args:
            current_tick: Current tick

        Returns:
            List of capability names
        """
        caps = set()
        for token in self._tokens:
            if not token.is_expired(current_tick):
                caps.update(token.capabilities)
        return list(caps)
