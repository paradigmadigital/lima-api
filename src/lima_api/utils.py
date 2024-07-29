import inspect
import re
from enum import Enum
from types import MappingProxyType
from typing import (
    Any,
    Optional,
    TypeVar,
    Union,
    get_args,
    get_origin,
)

try:
    from types import UnionType
except ImportError:
    UnionType = Union

from pydantic import BaseModel
from pydantic.fields import FieldInfo

from .config import PYDANTIC_V2, settings
from .parameters import LimaParameter, Location, QueryParameter

if PYDANTIC_V2:
    from pydantic import TypeAdapter
    from pydantic.fields import PydanticUndefined

    parse_raw_as = None
else:
    from pydantic.fields import Undefined as PydanticUndefined

    TypeAdapter = None
    from pydantic import parse_raw_as

from .exceptions import LimaException

BRACKET_REGEX = re.compile(settings.lima_bracket_regex)

T = TypeVar("T")


def parse_data(parse_class: type[T], data: bytes) -> Any:
    if parse_class is None:
        return
    if not data and get_origin(parse_class) in {UnionType, Union} and type(None) in get_args(parse_class):
        return
    if type(data) == parse_class:  # noqa: E721
        return data
    try:
        if PYDANTIC_V2:
            parse_model = TypeAdapter(parse_class)
            return parse_model.validate_json(data)
        else:
            return parse_raw_as(parse_class, data)
    except Exception as ex:
        if parse_class == Any:
            return data
        raise ex


def get_request_params(query_params_mapping: list[dict], kwargs: dict, undefined_values: tuple[Any, ...]) -> dict:
    params = {}
    for param_map in query_params_mapping:
        if param_map["kwargs_name"] not in kwargs and "default" not in param_map:
            raise TypeError(f"required argument missing <{param_map['kwargs_name']}>")
        argument_value = (
            kwargs[param_map["kwargs_name"]] if param_map["kwargs_name"] in kwargs else param_map["default"]
        )
        if argument_value in undefined_values:
            continue

        model_dump_mode = param_map.get("model_dump_mode", None)
        is_model = isinstance(argument_value, BaseModel)
        is_enum = issubclass(param_map["class"], Enum)
        if is_model and model_dump_mode in [QueryParameter.DUMP_DICT, QueryParameter.DUMP_DICT_NONE]:
            if PYDANTIC_V2:
                params.update(argument_value.model_dump(exclude_none=bool(model_dump_mode == QueryParameter.DUMP_DICT)))
            else:
                params.update(argument_value.dict(exclude_none=bool(model_dump_mode == QueryParameter.DUMP_DICT)))
        elif is_model and model_dump_mode in [QueryParameter.DUMP_JSON, QueryParameter.DUMP_JSON_NONE]:
            params[param_map["api_name"]] = argument_value.json(
                exclude_none=bool(model_dump_mode == QueryParameter.DUMP_JSON)
            )
        elif is_enum and isinstance(argument_value, Enum):
            params[param_map["api_name"]] = argument_value.value
        elif is_enum and isinstance(argument_value, (list, tuple)):
            params[param_map["api_name"]] = [item.value if hasattr(item, "value") else item for item in argument_value]
        else:
            params[param_map["api_name"]] = argument_value
    return params


def get_mappings(path: str, parameters: MappingProxyType[str, inspect.Parameter], method: str) -> tuple:
    path_params = BRACKET_REGEX.findall(path)

    query_params_mapping: list[dict] = []
    path_params_mapping: list[dict] = []
    header_mapping: list[dict] = []
    body_mapping: Optional[dict] = None

    for param_name, parameter in ((k, v) for k, v in parameters.items() if k not in ["self", "args", "kwargs"]):
        if parameter.kind != inspect.Parameter.KEYWORD_ONLY:
            raise ValueError("positional parameters are not supported, use funct(self, *, ...)")
        attrs = get_args(parameter.annotation)
        param_map = {
            "api_name": (
                parameter.default.alias
                if isinstance(parameter.default, FieldInfo) and parameter.default.alias is not None
                else param_name
            ),
            "kwargs_name": param_name,
            "class": (attrs[0] if attrs else parameter.annotation),
            "wrap": (parameter.annotation if attrs else None),
        }

        # Default values
        if isinstance(parameter.default, FieldInfo) and parameter.default.default is not PydanticUndefined:
            param_map["default"] = parameter.default.default
        elif not isinstance(parameter.default, FieldInfo) and parameter.default != parameter.empty:
            param_map["default"] = parameter.default

        if isinstance(parameter.default, QueryParameter):
            param_map["model_dump_mode"] = parameter.default.model_dump_mode

        # param type processing
        location = Location.QUERY
        if isinstance(parameter.default, LimaParameter):
            location = parameter.default.location
        elif issubclass(param_map["class"], BaseModel):
            location = Location.BODY
            if method == "GET":
                location = Location.QUERY
                param_map["model_dump_mode"] = QueryParameter.DUMP_DICT
        elif issubclass(param_map["class"], (list, tuple, dict)):
            location = Location.QUERY if method == "GET" else Location.BODY
        elif param_map["api_name"] in path_params:
            location = Location.PATH

        if location == Location.QUERY:
            query_params_mapping.append(param_map)
        elif location == Location.PATH:
            path_params_mapping.append(param_map)
        elif location == Location.BODY:
            if body_mapping:
                raise ValueError("too many body params")
            body_mapping = param_map
        elif location == Location.HEADER:
            header_mapping.append(param_map)
        else:
            raise ValueError("invalid location")

    missing_path_params = set(path_params) - {p["api_name"] for p in path_params_mapping}
    if missing_path_params:
        raise LimaException(f"path parameters need to be defined: <{','.join(missing_path_params)}>")

    return query_params_mapping, path_params_mapping, body_mapping, header_mapping


def get_body(body_mapping: Optional[dict], kwargs: dict):
    if body_mapping:
        if issubclass(body_mapping["class"], BaseModel):
            if PYDANTIC_V2:
                body_class = TypeAdapter(body_mapping["wrap"] if body_mapping["wrap"] else body_mapping["class"])
                body = body_class.validate_python(kwargs[body_mapping["kwargs_name"]])
                if not isinstance(body, list):
                    body = body.model_dump(exclude_none=True)
                else:
                    body = [item.model_dump(exclude_none=True) for item in body]
            else:
                body_class = body_mapping["class"]
                args = kwargs[body_mapping["kwargs_name"]]
                if not isinstance(args, list):
                    body = body_class.parse_obj(args).dict(exclude_none=True)
                else:
                    body = [body_class.parse_obj(item).dict(exclude_none=True) for item in args]
        else:
            body = kwargs[body_mapping["kwargs_name"]]
            if not isinstance(body, (list, tuple, dict)):
                body = {body_mapping["api_name"]: body}
    else:
        body = None
    return body


def get_final_url(url: str, path_params_mapping: dict, kwargs: dict) -> str:
    for param_map in path_params_mapping:
        url = url.replace(f"{{{param_map['api_name']}}}", f"{kwargs[param_map['kwargs_name']]}")
    return url
