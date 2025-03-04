import asyncio
from typing import Optional

import httpx
import pytest
from client import (
    AsyncClient,
    Item,
    ItemNotFound,
    LoginDataValidate,
    SyncClient,
    SyncDeclarativeConfClient,
    TooManyRequestError,
    UnexpectedError,
)
from freezegun import freeze_time
from httpx._types import HeaderTypes

import lima_api
from lima_api.config import settings


class TestAsyncLimaApi:
    def test_sync_client(self, mocker):
        client_mock = mocker.patch("httpx.Client").return_value.__enter__
        client = AsyncClient(base_url="http://localhost/")
        client.client = httpx.AsyncClient(transport=client.transport, timeout=client.timeout)

        with pytest.raises(lima_api.LimaException) as exc_info:
            client.sync_list()

        assert not client_mock.return_value.send.called
        assert str(exc_info.value.detail) == "sync function in async client"

    def test_warning_async_on_sync_client(self, mocker):
        client_mock = mocker.patch("httpx.Client").return_value.__enter__
        client = AsyncClient(base_url="http://localhost/")
        client.client = httpx.AsyncClient(transport=client.transport, timeout=client.timeout)

        with pytest.raises(lima_api.LimaException) as exc_info:
            client.sync_list()

        assert not client_mock.return_value.send.called
        assert str(exc_info.value.detail) == "sync function in async client"

    def test_warning_sync_on_async_client(self, mocker):
        client_mock = mocker.patch("httpx.Client").return_value.__enter__
        with (
            SyncClient(base_url="http://localhost/") as client,
            pytest.raises(lima_api.LimaException) as exc_info,
        ):
            asyncio.run(client.async_on_sync())

        assert not client_mock.return_value.send.called
        assert str(exc_info.value.detail) == "async function in sync client"


class TestLimaApi:
    """
    TestClient
    """

    def setup_method(self):
        self.client_cls = SyncClient

    def test_init(self):
        client = lima_api.LimaApi(base_url="http://localhost:8080")
        assert client.base_url == "http://localhost:8080"

    def test_client_not_init_with_sync_call(self, mocker):
        client_mock = mocker.patch("httpx.Client").return_value.__enter__.return_value
        client = self.client_cls(base_url="http://localhost/")

        with pytest.raises(lima_api.LimaException) as exc_info:
            client.sync_list()

        assert str(exc_info.value) == "uninitialized client"
        assert not client_mock.send.called

    def test_client_not_init_with_auto_start(self, mocker):
        client_mock = mocker.patch("httpx.Client").return_value.__enter__.return_value
        client_mock.send.return_value.status_code = 200
        client_mock.send.return_value.content = b'[{"id":1, "name": "test"}]'

        client = self.client_cls(base_url="http://localhost/", auto_start=True)
        client.sync_list()

        assert client_mock.send.called
        assert client.client is None

    def test_client_not_init_with_auto_start_and_not_auto_close(self, mocker):
        client_mock = mocker.patch("httpx.Client").return_value.__enter__.return_value
        client_mock.send.return_value.status_code = 200
        client_mock.send.return_value.content = b'[{"id":1, "name": "test"}]'

        client = self.client_cls(base_url="http://localhost/", auto_start=True, auto_close=False)
        client.sync_list()

        assert client_mock.send.called
        assert client.client is not None

    def test_client_field_required(self, mocker):
        client_mock = mocker.patch("httpx.Client").return_value.__enter__

        with (
            self.client_cls(base_url="http://localhost/") as client,
            pytest.raises(lima_api.ValidationError) as exc_info,
        ):
            client.sync_list_field_required()

        assert str(exc_info.value) == "required argument missing <limit>"
        assert not client_mock.return_value.send.called

    def test_client_init_with_sync_call(self, mocker):
        client_mock = mocker.patch("httpx.Client").return_value.__enter__.return_value
        client_mock.send.return_value.status_code = 200
        client_mock.send.return_value.content = b'[{"id":1, "name": "test"}]'

        client = self.client_cls(base_url="http://localhost/")
        client.start_client()
        response = client.sync_list()

        assert client_mock.send.called
        assert len(response) == 1
        assert response[0] == Item(id=1, name="test")

    def test_client_mapping_error_for_sync_call(self, mocker):
        client_mock = mocker.patch("httpx.Client").return_value.__enter__
        client_mock.return_value.send.return_value.status_code = 404
        client_mock.return_value.send.return_value.content = "File not found"

        with self.client_cls(base_url="http://localhost/") as client, pytest.raises(ItemNotFound) as exc_info:
            client.sync_list()

        assert client_mock.return_value.send.called
        assert str(exc_info.value.content) == "File not found"
        assert str(exc_info.value.status_code) == "404"
        assert str(exc_info.value.detail) == "Http Code 404 in response_mapping"

    def test_client_generic_error_for_sync_call(self, mocker):
        client_mock = mocker.patch("httpx.Client").return_value.__enter__.return_value
        client_mock.send.return_value.status_code = 503
        client_mock.send.return_value.content = b"Service Unavailable"

        with self.client_cls(base_url="http://localhost/") as client, pytest.raises(UnexpectedError) as exc_info:
            client.sync_list()

        assert client_mock.send.called
        assert exc_info.value.content == b"Service Unavailable"
        assert exc_info.value.status_code == 503
        assert exc_info.value.detail == "Http Code 503 not in response_mapping"

    def test_client_no_headers(self, mocker):
        client_mock = mocker.patch("httpx.Client").return_value.__enter__
        client_mock.return_value.send.return_value.status_code = 200
        client_mock.return_value.send.return_value.content = b""

        with self.client_cls(base_url="http://localhost") as client:
            client.do_login(
                path_arg="test",
                login=LoginDataValidate(
                    username="username",
                    password="password",
                    client_id="client_id",
                    grant_type="grant_type",
                ),
            )

        assert client_mock.return_value.build_request.called
        assert client_mock.return_value.build_request.call_args.args == (
            "POST",
            "http://localhost/realms/token/test/",
        )
        request_kwargs = client_mock.return_value.build_request.call_args.kwargs
        assert "headers" in request_kwargs
        assert request_kwargs.get("headers") == {}
        assert "data" not in request_kwargs
        assert "json" in request_kwargs
        assert request_kwargs["json"] == {
            "username": "username",
            "password": "password",
            "client_id": "client_id",
            "grant_type": "grant_type",
        }

    def test_client_with_headers(self, mocker):
        client_mock = mocker.patch("httpx.Client").return_value.__enter__
        client_mock.return_value.send.return_value.status_code = 200
        client_mock.return_value.send.return_value.content = b""

        with self.client_cls(base_url="http://localhost") as client:
            client.do_login_form(
                login=LoginDataValidate(
                    username="username",
                    password="password",
                    client_id="client_id",
                    grant_type="grant_type",
                )
            )

        assert client_mock.return_value.build_request.called
        method, url = client_mock.return_value.build_request.call_args.args
        assert method, url == ("POST", "http://localhost/realms/token/form")
        request_kwargs = client_mock.return_value.build_request.call_args.kwargs
        assert "headers" in request_kwargs
        assert request_kwargs.get("headers") == {"content-type": "application/x-www-form-urlencoded"}
        assert "json" not in request_kwargs
        assert "data" in request_kwargs
        assert request_kwargs["data"] == {
            "username": "username",
            "password": "password",
            "client_id": "client_id",
            "grant_type": "grant_type",
        }

    def test_fix_two_calls_with_auto_close_without_auto_start(self, mocker):
        client_mock = mocker.patch("httpx.Client").return_value.__enter__
        client_mock.return_value.send.return_value.status_code = 200
        client_mock.return_value.send.return_value.content = b""

        with self.client_cls(base_url="http://localhost", auto_start=False, auto_close=True) as client:
            client.sync_get_bytes()
            client.sync_get_bytes()

        assert client.auto_close is False

    def test_client_get_bytes_json(self, mocker):
        client_mock = mocker.patch("httpx.Client").return_value.__enter__
        client_mock.return_value.send.return_value.status_code = 200
        client_mock.return_value.send.return_value.content = b'[{"id": 1, "name": "test"}]'

        client = self.client_cls(base_url="http://localhost/")
        client.start_client()
        response = client.sync_get_bytes()

        assert client_mock.return_value.send.called
        assert response == b'[{"id": 1, "name": "test"}]'

    def test_client_get_bytes_no_json(self, mocker):
        client_mock = mocker.patch("httpx.Client").return_value.__enter__
        client_mock.return_value.send.return_value.status_code = 200
        client_mock.return_value.send.return_value.content = b"Just a test"

        client = self.client_cls(base_url="http://localhost/")
        client.start_client()
        response = client.sync_get_bytes()

        assert client_mock.return_value.send.called
        assert response == b"Just a test"

    def test_client_get_any_json(self, mocker):
        client_mock = mocker.patch("httpx.Client").return_value.__enter__
        client_mock.return_value.send.return_value.status_code = 200
        client_mock.return_value.send.return_value.content = b'[{"id": 1, "name": "test"}]'

        client = self.client_cls(base_url="http://localhost/")
        client.start_client()
        response = client.sync_get_any()

        assert client_mock.return_value.send.called
        assert response == [{"id": 1, "name": "test"}]

    def test_client_get_any_no_json(self, mocker):
        client_mock = mocker.patch("httpx.Client").return_value.__enter__
        client_mock.return_value.send.return_value.status_code = 200
        client_mock.return_value.send.return_value.content = b"Just a test"

        client = self.client_cls(base_url="http://localhost/")
        client.start_client()
        response = client.sync_get_any()

        assert client_mock.return_value.send.called
        assert response == b"Just a test"


class TestDeclarativeConfLimaApi(TestLimaApi):
    """
    TestClient
    """

    def setup_method(self):
        self.client_cls = SyncDeclarativeConfClient


class TestRetryProcessorLimaApi(TestLimaApi):
    def setup_method(self):
        self.client_cls = SyncClient

    def mock_httpx_response(
        self,
        mocker,
        status_code: httpx.codes = 200,
        content: bytes = b"",
        headers: Optional[HeaderTypes] = None,
    ):
        client_mock = mocker.patch("httpx.Client").return_value.__enter__
        client_mock.return_value.send.return_value.status_code = status_code
        client_mock.return_value.send.return_value.content = content
        client_mock.return_value.send.return_value.headers = headers or {}
        return client_mock

    def check_retry_after(self, mocker, retry_header, expected_call_value):
        httpx_mock = self.mock_httpx_response(
            mocker,
            httpx.codes.TOO_MANY_REQUESTS,
            b"",
            {"Retry-After": retry_header} if retry_header else None,
        )
        sync_sleep = mocker.patch("lima_api.retry_processors.sleep")
        async_sleep = mocker.patch("asyncio.sleep")

        with self.client_cls(base_url="http://localhost/") as client, pytest.raises(TooManyRequestError):
            client.sync_list()
        assert httpx_mock.return_value.send.call_count == settings.lima_retry_after_max_retries + 1
        assert sync_sleep.call_count == settings.lima_retry_after_max_retries
        assert sync_sleep.call_args.args == (expected_call_value,)
        assert async_sleep.call_count == 0

    def test_unauthorized_call_to_autologin_without_function(self, mocker):
        httpx_mock = self.mock_httpx_response(mocker, httpx.codes.UNAUTHORIZED)
        with self.client_cls(base_url="http://localhost/") as client, pytest.raises(UnexpectedError):
            client.sync_list()

        assert httpx_mock.return_value.send.call_count == settings.lima_autologin_max_retries + 1

    def test_unauthorized_call_to_autologin_with_function(self, mocker):
        httpx_mock = self.mock_httpx_response(mocker, httpx.codes.UNAUTHORIZED)

        with self.client_cls(base_url="http://localhost/") as client, pytest.raises(UnexpectedError):
            client.autologin = mocker.Mock(return_value=False)
            client.sync_list()

        assert httpx_mock.return_value.send.call_count == 1
        assert client.autologin.call_count == 1

    def test_retry_after_by_int_min_wait(self, mocker):
        self.check_retry_after(mocker, "1", settings.lima_retry_after_min_sleep_sec)

    def test_retry_after_by_int(self, mocker):
        self.check_retry_after(mocker, "120", 120)

    @freeze_time("2025-02-28")
    def test_retry_after_by_str_min_wait(self, mocker):
        self.check_retry_after(mocker, "Fri, 28 Feb 2025 00:00:01 GMT", settings.lima_retry_after_min_sleep_sec)

    @freeze_time("2025-02-28")
    def test_retry_after_by_str(self, mocker):
        self.check_retry_after(mocker, "Fri, 28 Feb 2025 00:02:00 GMT", 120)

    def test_retry_after_by_wrong_str(self, mocker):
        self.check_retry_after(mocker, "Invalid value", settings.lima_retry_after_min_sleep_sec)

    def test_retry_after_without_header(self, mocker):
        self.check_retry_after(mocker, None, settings.lima_retry_after_min_sleep_sec)
