from typing import Any, Dict, Mapping


def sanitize_key(key: str, obj_type: str) -> str:
    if obj_type == 'package':
        if key == 'type':
            return 'pkg_type'

    return key


def sanitize_value(key: str, value: Any, obj_type: str) -> Any:
    if obj_type == 'package':
        if key == 'releases':
            from .types import VSPackageRel
            return [VSPackageRel.from_dict(release) for release in value]

    return value


def sanitize_dict(obj: Mapping[str, Any], obj_type: str) -> Dict[str, Any]:
    return {
        sanitize_key(key, obj_type): sanitize_value(key, value, obj_type)
        for key, value in obj.items()
    }
