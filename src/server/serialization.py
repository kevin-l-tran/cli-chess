from dataclasses import asdict, is_dataclass
from typing import Any, cast


def to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        if isinstance(value, type):
            raise TypeError(
                f"Expected dataclass instance, got dataclass type: {value!r}"
            )

        return to_jsonable(asdict(cast(Any, value)))

    if isinstance(value, dict):
        return {str(to_jsonable(key)): to_jsonable(item) for key, item in value.items()}

    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]

    if isinstance(value, set):
        return [to_jsonable(item) for item in sorted(value, key=repr)]

    return value
