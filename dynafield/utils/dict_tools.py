import copy
from typing import Any, Dict


def merge_dict_data(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively merges two dictionaries with special handling for lists and nested dictionaries.
    - For non-list/non-dict values, dict2's values take precedence
    - For lists, dict2's list completely replaces dict1's
    - For nested dictionaries, merges recursively

    Args:
        dict1: Base dictionary
        dict2: Dictionary to merge into dict1 (takes precedence)

    Returns:
        New merged dictionary (inputs are not modified)
    """
    merged: Dict[str, Any] = {}
    all_keys = dict1.keys() | dict2.keys()  # Union of keys

    for key in all_keys:
        val1 = dict1.get(key)
        val2 = dict2.get(key)

        if val1 is not None and val2 is not None:
            if isinstance(val1, dict) and isinstance(val2, dict):
                merged[key] = merge_dict_data(val1, val2)
            elif isinstance(val1, list) and isinstance(val2, list):
                merged[key] = copy.deepcopy(val2)
            else:
                merged[key] = copy.deepcopy(val2)
        elif val1 is not None:
            merged[key] = copy.deepcopy(val1)
        else:
            merged[key] = copy.deepcopy(val2)

    return merged


def check_empty_dict_data(data: Dict[str, Any]) -> bool:
    return not bool(data)
