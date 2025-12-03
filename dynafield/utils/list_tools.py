def is_in_list(value: str | None, values: list[str]) -> bool:
    """Check if a value exists in a list of strings or within numeric ranges.

    Args:
        value: The value to check (can be string or None)
        values: List of strings to check against (can contain ranges like "1-10")

    Returns:
        bool: True if value is found in the list or within any range, False otherwise
    """
    # Early return for None case
    if value is None:
        return False

    # Fast path: direct string match
    if value in values:
        return True

    # Try numeric comparison only if direct match fails
    try:
        num_value = int(value)
    except ValueError:
        return False

    # Check for range matches
    for item in values:
        if "-" in item:
            parts = item.split("-", maxsplit=1)  # Split only on first hyphen
            if len(parts) != 2:
                continue
            try:
                start, end = map(int, parts)
                if start <= num_value <= end:
                    return True
            except ValueError:
                continue

    return False
