from enum import Enum


class Location(str, Enum):
    """
    Enum that indicate the location of data.
    """
    PATH = "PATH"
    QUERY = "QUERY"
    BODY = "BODY"
    HEADER = "HEADER"
    FILE = "FILE"


class DumpMode(str, Enum):
    """
    Enum that indicate how dump the data.
    """
    DICT = "dict"
    DICT_NONE = "dict_none"
    JSON = "json"
    JSON_NONE = "json_none"


class KwargsMode(str, Enum):
    """
    Enum that indicate how manage the kwargs that are not defined.
    """
    IGNORE = "ignore"
    QUERY = "query"
    BODY = "body"
