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
    """
    Dump payload as a dict without the none values.
    """
    DICT_NONE = "dict_none"
    """
    Dump payload as a dict with the none values.
    """
    JSON = "json"
    """
    Dump payload as a json without the null values.
    """
    JSON_NONE = "json_none"
    """
    Dump payload as a json with the null values.
    """


class KwargsMode(str, Enum):
    """
    .. versionadded:: 1.4.3

    Enum that indicate how manage the kwargs that are not defined.
    """

    IGNORE = "ignore"
    """
    Do not send kwargs.
    """
    QUERY = "query"
    """
    Send all the kwargs as query parameters.
    """
    BODY = "body"
    """
    Send all the kwargs as body parameters.
    """
