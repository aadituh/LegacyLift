"""Estimate translation tokens without a tokenizer.

Example:
    >>> from legacylift.providers.config import RoutingRules
    >>> estimate_total("abcd", RoutingRules(chars_per_token=3.5, output_token_ratio=1))
    4
"""

import math

from legacylift.providers.config import CHARS_PER_TOKEN, OUTPUT_TOKEN_RATIO, RoutingRules


def estimate_input_tokens(text: str, *, chars_per_token: float = CHARS_PER_TOKEN) -> int:
    """Estimate input tokens as characters divided by ``chars_per_token``.

    Args:
        text: Source text.
        chars_per_token: Divisor. The default is :data:`CHARS_PER_TOKEN`.

    Returns:
        ``0`` for an empty string, otherwise the ceiling of the division.
    """
    if not text or chars_per_token <= 0:
        return 0
    return math.ceil(len(text) / chars_per_token)


def estimate_total(text: str, rules: RoutingRules | None = None) -> int:
    """Estimate input tokens plus reserved output tokens.

    Args:
        text: Source text.
        rules: Routing numbers. ``None`` uses the module defaults.

    Returns:
        Input estimate plus ``ceil(input * output_token_ratio)``.
    """
    active = rules or RoutingRules()
    incoming = estimate_input_tokens(text, chars_per_token=active.chars_per_token)
    if active.output_token_ratio <= 0:
        return incoming
    return incoming + math.ceil(incoming * active.output_token_ratio)


def format_tokens(count: int) -> str:
    """Format a token count for a routing note.

    Args:
        count: Token count. Negative values are treated as zero.

    Returns:
        ``999`` below one thousand, otherwise a short form such as ``1.2k``.

    Example:
        >>> format_tokens(1200)
        '1.2k'
    """
    value = max(count, 0)
    if value < 1000:
        return str(value)
    scaled = value / 1000
    text = f"{scaled:.1f}".rstrip("0").rstrip(".")
    return f"{text}k"


# Re-export the ratio so callers can name the constant without importing config.
__all__ = ["CHARS_PER_TOKEN", "OUTPUT_TOKEN_RATIO", "estimate_input_tokens", "estimate_total", "format_tokens"]
