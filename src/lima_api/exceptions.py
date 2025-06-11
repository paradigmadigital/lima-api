import contextlib
import json
from typing import Any, Optional, TypeVar, Union

import httpx
import pydantic

from .utils import parse_data

T = TypeVar("T")


class LimaException(Exception):
    detail: str = ""
    model: Optional[T] = None

    def __init__(
        self,
        detail: Optional[str] = None,
        status_code: Optional[Union[httpx.codes, int]] = None,
        content: Optional[bytes] = None,
        request: Optional[httpx.Request] = None,
        response: Optional[httpx.Response] = None,
    ):
        if detail is not None:
            self.detail = detail
        self._status_code: Optional[Union[httpx.codes, int]] = status_code
        self._content: Optional[bytes] = content
        self._request: Optional[httpx.Request] = request
        self._response: Optional[httpx.Response] = response

    @property
    def http_request(self):
        if self._request is None and self._response:
            self._request = self._response.request
        return self._request

    @property
    def http_response(self):
        return self._response

    @property
    def status_code(self) -> Optional[Union[httpx.codes, int]]:
        if self._status_code is None and self._response:
            self._status_code = self._response.status_code
        return self._status_code

    @status_code.setter
    def status_code(self, status_code: Optional[Union[httpx.codes, int]]):
        self._status_code = status_code

    @property
    def content(self) -> Optional[bytes]:
        if self._content is None and self._response:
            self._content = self._response.content
        return self._content

    @content.setter
    def content(self, content: bytes):
        self._content = content

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        return f"{class_name}(detail={self.detail!r}, status_code={self.status_code!r})"

    def __str__(self) -> str:
        return self.detail

    def json(self, default: Optional[Any] = dict):
        """
        Return the JSON-decoded content of the response.

        If the content is None, return the provided default value.
        The default value can be a callable, in which case it is called
        to obtain the return value.

        :param default: The default value to return if content is None.
        :return: The JSON-decoded content or the default value.
        :raises json.JSONDecodeError: If the content cannot be decoded.
        """
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
