from typing import Union


def format_duration(duration_str: str) -> str:
    """Format duration string for display"""
    if not duration_str or duration_str == "":
        return "0:00"
    return duration_str


def format_number(num: Union[int, float, str, None]) -> str:
    """Format large numbers with K, M, B suffixes"""
    try:
        value = float(num)  # type: ignore[arg-type]
        if value >= 1_000_000_000:
            return f"{value/1_000_000_000:.1f}B"
        if value >= 1_000_000:
            return f"{value/1_000_000:.1f}M"
        if value >= 1_000:
            return f"{value/1_000:.1f}K"
        return str(int(value))
    except (ValueError, TypeError):
        return "0"


