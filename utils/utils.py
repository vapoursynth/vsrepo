from typing import Any, Dict, Mapping


def sanitize_key(key: str, obj_type: str) -> str:
    if obj_type == 'package':
        if key == 'type':
            return 'pkg_type'

    return key


def sanitize_keys(obj: Mapping[str, Any], obj_type: str) -> Dict[str, Any]:
    return {
        sanitize_key(key, obj_type): value
        for key, value in obj.items()
    }
