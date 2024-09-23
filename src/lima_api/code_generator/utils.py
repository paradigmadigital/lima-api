import re
import unicodedata
from enum import Enum


class OpenApiType(str, Enum):
    STRING = "string"
    BOOLEAN = "boolean"
    INTEGER = "integer"
    NUMBER = "number"
    ARRAY = "array"
    NULL = "null"


OPENAPI_2_TYPE_MAPPING: dict[OpenApiType | str, str] = {
    OpenApiType.STRING: "str",
    OpenApiType.BOOLEAN: "bool",
    OpenApiType.INTEGER: "int",
    OpenApiType.NUMBER: "float",
    OpenApiType.ARRAY: "list",
    OpenApiType.NULL: "None",
}

CAMEL2SNAKE_RE = re.compile("([A-Za-z0-9][a-z0-9]*)")
CAMEL2SNAKE_CONSECUTIVE_RE = re.compile("((?:[A-Z]+|[a-z0-9])[a-z0-9]*)")
START_WITH_UPPER = re.compile("^[A-Z]")


def strip_accents(text: str) -> str:
    """
    Replace accent characters in a String
    :param text: String to cast
    :return: Formated String
    """
    text = unicodedata.normalize("NFD", text)
    text = text.encode("ascii", "ignore")
    text = text.decode("utf-8")
    return str(text)


def camel_to_snake(camel_str: str, preserve_upper_consecutive=True) -> str:
    camel_str = strip_accents(camel_str)
    regex = CAMEL2SNAKE_RE
    if preserve_upper_consecutive:
        regex = CAMEL2SNAKE_CONSECUTIVE_RE
    groups = regex.findall(camel_str.replace(" ", "_").replace(".", ""))
    return "_".join([i.lower() for i in groups])


def snake_to_camel(snake_str: str) -> str:
    if not snake_str:
        return ""
    snake_str = strip_accents(snake_str)
    snake_str = snake_str.encode("ascii", "ignore").decode("ascii")
    _str = snake_str.replace("-", "_").replace(" ", "_").replace(".", "")
    return "".join(x if START_WITH_UPPER.match(x) else x[0].upper() + x[1:] if x else "" for x in _str.split("_"))
