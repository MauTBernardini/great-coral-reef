import json
from dataclasses import asdict, is_dataclass
from enum import Enum


def to_jsonable(obj):
    if is_dataclass(obj):
        return to_jsonable(asdict(obj))
    if isinstance(obj, dict):
        return {to_jsonable(k): to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(v) for v in obj]
    if isinstance(obj, Enum):
        return obj.value
    return obj


def dumps(obj) -> str:
    return json.dumps(to_jsonable(obj), ensure_ascii=False, indent=2)
