import contextlib
import json
from typing import Optional, TypeVar, Union

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
        self.status_code = status_code
        self.content = content

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        return f"{class_name}(detail={self.detail!r}, status_code={self.status_code!r})"

    def __str__(self) -> str:
        return self.detail

    def json(self):
        return json.loads(self.content.decode())

    def object(self):
        return parse_data(self.model, self.content)

    def response(self) -> Union[T, dict, bytes]:
        response = self.content
        if self.content:
            with contextlib.suppress(json.JSONDecodeError):
                response = self.json()
                if self.model:
                    with contextlib.suppress(pydantic.ValidationError):
                        response = self.object()
        return response


class ValidationError(LimaException):
    detail = "Validation error"
