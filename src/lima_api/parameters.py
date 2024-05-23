from enum import Enum

from pydantic.fields import FieldInfo


class Location(str, Enum):
    PATH = "PATH"
    QUERY = "QUERY"
    BODY = "BODY"


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


class QueryParameter(LimaParameter):
    DUMP_DICT = "dict"
    DUMP_DICT_NONE = "dict_none"
    DUMP_JSON = "json"
    DUMP_JSON_NONE = "json_none"

    def __init__(self, model_dump_mode=DUMP_DICT, **kwargs):
        super().__init__(Location.QUERY, **kwargs)
        self.model_dump_mode = model_dump_mode


class BodyParameter(LimaParameter):
    def __init__(self, *args, **kwargs):
        super().__init__(Location.BODY, **kwargs)
