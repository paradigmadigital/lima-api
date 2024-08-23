import asyncio

import httpx
import pytest
from client import (
    AsyncClient,
    Item,
    ItemNotFound,
    LoginDataValidate,
    SyncClient,
    SyncDeclarativeConfClient,
    UnexpectedError,
)

import lima_api


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

    def test_client_field_required(self, mocker):
        client_mock = mocker.patch("httpx.Client").return_value.__enter__

        with self.client_cls(base_url="http://localhost/") as client, pytest.raises(TypeError) as exc_info:
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
        assert str(exc_info.value.detail) == "Http Code in response_mapping"

    def test_client_generic_error_for_sync_call(self, mocker):
        client_mock = mocker.patch("httpx.Client").return_value.__enter__.return_value
        client_mock.send.return_value.status_code = 503
        client_mock.send.return_value.content = "Service Unavailable"

        with self.client_cls(base_url="http://localhost/") as client, pytest.raises(UnexpectedError) as exc_info:
            client.sync_list()

        assert client_mock.send.called
        assert str(exc_info.value.content) == "Service Unavailable"
        assert str(exc_info.value.status_code) == "503"
        assert str(exc_info.value.detail) == "Http Code not in response_mapping"

    def test_client_no_headers(self, mocker):
        client_mock = mocker.patch("httpx.Client").return_value.__enter__
        client_mock.return_value.send.return_value.status_code = 200
        client_mock.return_value.send.return_value.content = ""

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
        client_mock.return_value.send.return_value.content = ""

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
