import asyncio
from unittest.mock import Mock

import httpx
import pydantic
import pytest
from client import (
    AsyncClient,
    SyncClient,
)

import lima_api


class CustomModel(pydantic.BaseModel):
    error: str


class CustomException(lima_api.LimaException):
    detail = "Custom Exception"
    model = CustomModel


class TestException:
    client_cls = SyncClient

    def make_query(self):
        with self.client_cls(base_url="http://localhost/") as client, pytest.raises(lima_api.LimaException) as exc_info:
            client.sync_list()
        return exc_info

    def get_mock_client(self, mocker):
        return mocker.patch("httpx.Client").return_value.__enter__.return_value

    def test_validation_error(self, mocker):
        client_mock = self.get_mock_client(mocker)
        client_mock.send.return_value.status_code = 200
        client_mock.send.return_value.content = b"Wrong format"

        exc_info = self.make_query()

        assert isinstance(exc_info.value, lima_api.ValidationError)
        assert exc_info.value.content == b"Wrong format"
        assert exc_info.value.status_code == 200
        assert exc_info.value.detail == "Validation error"
        assert isinstance(exc_info.value.__cause__, pydantic.ValidationError)

    def test_http_error_without_request(self, mocker):
        client_mock = self.get_mock_client(mocker)
        client_mock.build_request = Mock()
        client_mock.build_request.return_value.url = "http://localhost/"
        client_mock.send.side_effect = httpx.HTTPError("Internal Server Error")

        exc_info = self.make_query()

        err_msg = "Connection error http://localhost/ - <class 'httpx.HTTPError'> - Internal Server Error"
        assert exc_info.value.detail == err_msg
        assert isinstance(exc_info.value.__cause__, httpx.HTTPError)

    def test_http_error_with_request(self, mocker):
        client_mock = self.get_mock_client(mocker)
        exc = httpx.HTTPError("Internal Server Error")
        client_mock.send.side_effect = exc
        exc._request = type("FakeRequest", (object,), {"url": "http://fakeurl"})()

        exc_info = self.make_query()

        err_msg = "Connection error http://fakeurl - <class 'httpx.HTTPError'> - Internal Server Error"
        assert exc_info.value.detail == err_msg
        assert isinstance(exc_info.value.__cause__, httpx.HTTPError)


class TestAsyncException(TestException):
    client_cls = AsyncClient

    def get_mock_client(self, mocker):
        return mocker.patch("httpx.AsyncClient").return_value.__aenter__.return_value

    def make_query(self):
        async def query():
            with pytest.raises(lima_api.LimaException) as exc_info:
                async with self.client_cls(base_url="http://localhost/") as client:
                    await client.async_list()
            return exc_info

        return asyncio.run(query())


class TestExceptionClass:
    def setup_method(self):
        self.ex = CustomException(
            content=b'{"error": "Some error"}',
            status_code=404,
        )

    def test_repr(self):
        assert repr(self.ex) == "CustomException(detail='Custom Exception', status_code=404)"

    def test_json(self):
        assert self.ex.json() == {"error": "Some error"}

    def test_object(self):
        obj = self.ex.object()
        assert isinstance(obj, CustomModel)
        assert obj.error == "Some error"

    def test_response_wrong_json(self):
        ex = CustomException(
            content=b"Wrong json error",
            status_code=404,
        )
        assert ex.response() == b"Wrong json error"

    def test_response_wrong_model(self):
        ex = CustomException(
            content=b'"Wrong json error"',
            status_code=404,
        )
        assert ex.response() == "Wrong json error"

    def test_response(self):
        obj = self.ex.response()
        assert isinstance(obj, CustomModel)
        assert obj.error == "Some error"
