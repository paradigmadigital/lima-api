import re
from enum import Enum


class OpenApiType(str, Enum):
    STRING = "string"
    BOOLEAN = "boolean"
    INTEGER = "integer"
    NUMBER = "number"
    ARRAY = "array"


OPENAPI_2_TYPE_MAPPING: dict[OpenApiType, str] = {
    OpenApiType.STRING: "str",
    OpenApiType.BOOLEAN: "bool",
    OpenApiType.INTEGER: "int",
    OpenApiType.NUMBER: "float",
    OpenApiType.ARRAY: "list",
}

CAMEL2SNAKE_RE = re.compile("([A-Za-z0-9][a-z]*)")
START_WITH_UPPER = re.compile("^[A-Z]")


def camel_to_snake(camel_str: str) -> str:
    groups = CAMEL2SNAKE_RE.findall(camel_str.replace(" ", ""))
    return "_".join([i.lower() for i in groups])


def snake_to_camel(snake_str: str) -> str:
    _str = snake_str.replace("-", "_").replace(" ", "_")
    return "".join(
        x if START_WITH_UPPER.match(x) else x[0].upper() + x[1:]
        for x in _str.split("_")
    )
