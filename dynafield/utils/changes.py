from typing import Any, Dict, List, Optional, Set, Union


def recursive_diff(dict1: Dict[str, Any], dict2: Dict[str, Any], keys_to_exclude: Optional[List[str]] = None) -> Dict[str, Union[Any, None]]:
    """Return a dict with only the changed values from dict2, with removed keys set to None"""
    result: Dict[str, Union[Any, None]] = {}
    all_keys: Set[str] = set(dict1.keys()) | set(dict2.keys())

    for key in all_keys:
        if keys_to_exclude and key in keys_to_exclude:
            continue
        if key in dict1 and key in dict2:
            val1, val2 = dict1[key], dict2[key]

            if isinstance(val1, dict) and isinstance(val2, dict):
                nested_diff = recursive_diff(val1, val2)
                if nested_diff:
                    result[key] = nested_diff

            elif isinstance(val1, List) and isinstance(val2, List):
                if val1 != val2:
                    result[key] = val2

            elif val1 != val2:
                result[key] = val2

        elif key in dict2:
            # Key only in dict2 (added)
            result[key] = dict2[key]
        elif key in dict1:
            # Key only in dict1 (removed)
            result[key] = None

    return result
