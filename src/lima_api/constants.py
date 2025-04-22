from enum import Enum


class Location(str, Enum):
    PATH = "PATH"
    QUERY = "QUERY"
    BODY = "BODY"
    HEADER = "HEADER"
    FILE = "FILE"


class DumpMode(str, Enum):
    DICT = "dict"
    DICT_NONE = "dict_none"
    JSON = "json"
    JSON_NONE = "json_none"


class KwargsMode(str, Enum):
    IGNORE = "ignore"
    QUERY = "query"
    BODY = "body"
