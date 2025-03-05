from enum import Enum

from pydantic.fields import FieldInfo


class Location(str, Enum):
    PATH = "PATH"
    QUERY = "QUERY"
    BODY = "BODY"
    HEADER = "HEADER"


class LimaParameter(FieldInfo):
    def __init__(
        self,
        location: Location,
        **kwargs,
    ):
        self.location = location
        super().__init__(**kwargs)


class PathParameter(LimaParameter):
    def __init__(self, **kwargs):
        super().__init__(Location.PATH, **kwargs)


class DumpMode(str, Enum):
    DICT = "dict"
    DICT_NONE = "dict_none"
    JSON = "json"
    JSON_NONE = "json_none"


class QueryParameter(LimaParameter):
    def __init__(self, model_dump_mode: DumpMode = DumpMode.DICT, **kwargs):
        super().__init__(Location.QUERY, **kwargs)
        self.model_dump_mode = model_dump_mode


class BodyParameter(LimaParameter):
    def __init__(self, *args, **kwargs):
        super().__init__(Location.BODY, **kwargs)


class HeaderParameter(LimaParameter):
    def __init__(self, *args, **kwargs):
        super().__init__(Location.HEADER, **kwargs)
