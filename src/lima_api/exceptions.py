import contextlib
import json
from typing import Any, Optional, TypeVar, Union

import pydantic

from .utils import parse_data

T = TypeVar("T")


class LimaException(Exception):
    detail: str = ""
    model: Optional[T] = None

    def __init__(
        self,
        detail: Optional[str] = None,
        status_code: Optional[int] = None,
        content: Optional[bytes] = None,
    ):
        if detail is not None:
            self.detail = detail
        self.status_code: Optional[int] = status_code
        self.content: Optional[bytes] = content

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        return f"{class_name}(detail={self.detail!r}, status_code={self.status_code!r})"

    def __str__(self) -> str:
        return self.detail

    def json(self, default: Optional[Any] = dict):
        if self.content is None:
            return default() if callable(default) else default
        return json.loads(self.content.decode())

    def object(self):
        return parse_data(self.model, self.content)

    def response(self, default: Optional[Any] = dict) -> Union[bytes, Any, T]:
        response = self.content
        if self.content is not None:
            with contextlib.suppress(json.JSONDecodeError):
                response = self.json(default=default)
                if self.model:
                    with contextlib.suppress(pydantic.ValidationError):
                        response = self.object()
        else:
            response = default() if callable(default) else default
        return response


class ValidationError(LimaException):
    detail = "Validation error"

    def __str__(self):
        if getattr(self, "__cause__", None):
            return str(self.__cause__)
        return self.detail
