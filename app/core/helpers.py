def cap_limit(limit: int, max_limit: int = 200) -> int:
    """Cap the pagination limit to a maximum value."""
    return min(max(1, limit), max_limit)
