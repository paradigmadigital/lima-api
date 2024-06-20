import sys
from typing import Optional

import httpx
import lima_api
import pytest
from client import (
    AsyncClient,
    GenericError,
    Item,
    ItemNotFound,
    LoginDataValidate,
    SyncClient,
    SyncDeclarativeConfClient,
    UnexpectedError,
)
from lima_api.parameters import BodyParameter


class TestAsyncLimaApi:
    def test_sync_client(self, mocker):
        client_mock = mocker.patch("httpx.Client")
        client = AsyncClient(base_url="http://localhost/")
        client.client = httpx.AsyncClient(transport=client.transport, timeout=client.timeout)

        with pytest.raises(lima_api.LimaException) as exc_info:
            client.sync_list()

        assert not client_mock.return_value.send.called
        assert str(exc_info.value.detail) == "sync function in async client"

    def test_warning_async_on_sync_client(self, mocker):
        client_mock = mocker.patch("httpx.Client")
        client = AsyncClient(base_url="http://localhost/")
        client.client = httpx.AsyncClient(transport=client.transport, timeout=client.timeout)

        with pytest.raises(lima_api.LimaException) as exc_info:
            client.sync_list()

        assert not client_mock.return_value.send.called
        assert str(exc_info.value.detail) == "sync function in async client"


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
        client_mock = mocker.patch("httpx.Client")
        client = self.client_cls(base_url="http://localhost/")

        with pytest.raises(lima_api.LimaException) as exc_info:
            client.sync_list()

        assert str(exc_info.value) == "uninitialized client"
        assert not client_mock.return_value.send.called

    def test_client_field_required(self, mocker):
        client_mock = mocker.patch("httpx.Client")

        with self.client_cls(base_url="http://localhost/") as client, pytest.raises(TypeError) as exc_info:
            client.sync_list_field_required()

        assert str(exc_info.value) == "required argument missing <limit>"
        assert not client_mock.return_value.send.called

    def test_client_init_with_sync_call(self, mocker):
        client_mock = mocker.patch("httpx.Client")
        client_mock.return_value.send.return_value.status_code = 200
        client_mock.return_value.send.return_value.content = '[{"id":1, "name": "test"}]'

        client = self.client_cls(base_url="http://localhost/")
        client.start_client()
        response = client.sync_list()

        assert client_mock.return_value.send.called
        assert len(response) == 1
        assert response[0] == Item(id=1, name="test")

    def test_client_mapping_error_for_sync_call(self, mocker):
        client_mock = mocker.patch("httpx.Client")
        client_mock.return_value.send.return_value.status_code = 404
        client_mock.return_value.send.return_value.content = "File not found"

        with self.client_cls(base_url="http://localhost/") as client, pytest.raises(ItemNotFound) as exc_info:
            client.sync_list()

        assert client_mock.return_value.send.called
        assert str(exc_info.value.content) == "File not found"
        assert str(exc_info.value.status_code) == "404"
        assert str(exc_info.value.detail) == "Http Code in response_mapping"

    def test_client_generic_error_for_sync_call(self, mocker):
        client_mock = mocker.patch("httpx.Client")
        client_mock.return_value.send.return_value.status_code = 503
        client_mock.return_value.send.return_value.content = "Service Unavailable"

        with self.client_cls(base_url="http://localhost/") as client, pytest.raises(UnexpectedError) as exc_info:
            client.sync_list()

        assert client_mock.return_value.send.called
        assert str(exc_info.value.content) == "Service Unavailable"
        assert str(exc_info.value.status_code) == "503"
        assert str(exc_info.value.detail) == "Http Code not in response_mapping"

    def test_client_no_headers(self, mocker):
        client_mock = mocker.patch("httpx.Client")
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
        client_mock = mocker.patch("httpx.Client")
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


class TestDeclarativeConfLimaApi(TestLimaApi):
    """
    TestClient
    """

    def setup_method(self):
        self.client_cls = SyncDeclarativeConfClient


class TestLimaParameters:
    """
    TestClient
    """

    def setup_method(self):
        self.client_cls = SyncClient

    def test_init(self):
        client = lima_api.LimaApi(base_url="http://localhost:8080")
        assert client.base_url == "http://localhost:8080"

    def _mock_request(self, mocker, status_code: int = 200, content: str = "[]"):
        client_mock = mocker.patch("httpx.Client")
        client_mock.return_value.send.return_value.status_code = status_code
        client_mock.return_value.send.return_value.content = content
        return client_mock

    def test_get_params(self, mocker):
        client_mock = self._mock_request(mocker)

        with self.client_cls(base_url="http://localhost") as client:
            client.sync_list_query(limit=2)

        assert client_mock.return_value.build_request.called
        method, url = client_mock.return_value.build_request.call_args.args
        assert method, url == ("GET", "http://localhost/items/query")
        request_kwargs = client_mock.return_value.build_request.call_args.kwargs
        assert "params" in request_kwargs
        assert request_kwargs["params"] == {"limit": 2}

    def test_get_body(self, mocker):
        client_mock = self._mock_request(mocker)

        with self.client_cls(base_url="http://localhost") as client:
            client.sync_list_body(limit=2)

        assert client_mock.return_value.build_request.called
        method, url = client_mock.return_value.build_request.call_args.args
        assert method, url == ("GET", "http://localhost/items/body")
        request_kwargs = client_mock.return_value.build_request.call_args.kwargs
        assert "json" in request_kwargs
        assert request_kwargs["json"] == {"limit": 2}

    def test_get_path(self, mocker):
        client_mock = self._mock_request(mocker)

        with self.client_cls(base_url="http://localhost") as client:
            client.sync_list_path(limit=2)

        assert client_mock.return_value.build_request.called
        method, url = client_mock.return_value.build_request.call_args.args
        assert method, url == ("GET", "http://localhost/items/2")
        request_kwargs = client_mock.return_value.build_request.call_args.kwargs
        assert "json" in request_kwargs
        assert "data" not in request_kwargs
        assert request_kwargs["json"] is None
        assert request_kwargs["params"] == {}

    def test_get_models_params(self, mocker):
        client_mock = self._mock_request(mocker)

        with self.client_cls(base_url="http://localhost") as client:
            client.sync_list_model(params=Item(id=2, name="test"))

        assert client_mock.return_value.build_request.called
        method, url = client_mock.return_value.build_request.call_args.args
        assert method, url == ("GET", "http://localhost/items/query_model")
        request_kwargs = client_mock.return_value.build_request.call_args.kwargs
        assert "params" in request_kwargs
        assert request_kwargs["params"] == {"id": 2, "name": "test"}

    def test_all_params(self, mocker):
        client_mock = self._mock_request(mocker)

        with self.client_cls(base_url="http://localhost") as client:
            client.sync_all_params(path=1, query=2, body=Item(id=3, name="name"))

        assert client_mock.return_value.build_request.called
        method, url = client_mock.return_value.build_request.call_args.args
        assert method, url == ("GET", "http://localhost/items/1/all")
        request_kwargs = client_mock.return_value.build_request.call_args.kwargs
        assert "params" in request_kwargs
        assert request_kwargs["params"] == {"name": 2}
        assert "json" in request_kwargs
        assert request_kwargs["json"] == {"id": 3, "name": "name"}

    def test_many_body(self):
        with pytest.raises(ValueError) as exc_info:

            class SyncClient(lima_api.SyncLimaApi):
                @lima_api.get("/items/split", default_exception=GenericError)
                def sync_body_split(
                    self,
                    *,
                    body_1: str = BodyParameter(),
                    body_2: str = BodyParameter(),
                ) -> list[Item]: ...

        assert exc_info.value.args == ("too many body params",)

    def test_many_body_optionals(self):
        with pytest.raises(ValueError) as exc_info:

            class TestSyncClient(lima_api.SyncLimaApi):
                @lima_api.get("/items/split", default_exception=GenericError)
                def sync_kwargs_overwrite_item(
                    self,
                    *,
                    item: Optional[Item] = BodyParameter(default=None),
                    _id: Optional[int] = BodyParameter(default=None, alias="id"),
                    name: Optional[str] = BodyParameter(default=None),
                ) -> list[Item]: ...

        assert exc_info.value.args == ("too many body params",)

    def test_force_only_keywords(self, mocker):
        with pytest.raises(ValueError) as exc_info:

            class TestSyncClient(lima_api.SyncLimaApi):
                @lima_api.get("/items/split", default_exception=GenericError)
                def sync_kwargs_overwrite_item(
                    self, item: Optional[Item] = BodyParameter(default=None)
                ) -> list[Item]: ...

        assert exc_info.value.args == ("positional parameters are not supported, use funct(self, *, ...)",)

    def test_list_objects(self, mocker):
        client_mock = self._mock_request(mocker)

        with self.client_cls(base_url="http://localhost") as client:
            client.sync_list_objects(items=[Item(id=1, name="one"), Item(id=2, name="test")])

        assert client_mock.return_value.build_request.called
        method, url = client_mock.return_value.build_request.call_args.args
        assert method, url == ("GET", "http://localhost/items/query_model")
        request_kwargs = client_mock.return_value.build_request.call_args.kwargs
        assert "json" in request_kwargs
        assert request_kwargs["json"] == [{"id": 1, "name": "one"}, {"id": 2, "name": "test"}]

    def test_typing_objects(self, mocker):
        client_mock = self._mock_request(mocker)

        with self.client_cls(base_url="http://localhost") as client:
            client.sync_list_objects(items=[Item(id=1, name="one"), Item(id=2, name="test")])

        assert client_mock.return_value.build_request.called
        method, url = client_mock.return_value.build_request.call_args.args
        assert method, url == ("GET", "http://localhost/items/query_model")
        request_kwargs = client_mock.return_value.build_request.call_args.kwargs
        assert "json" in request_kwargs
        assert request_kwargs["json"] == [{"id": 1, "name": "one"}, {"id": 2, "name": "test"}]

    def test_header(self, mocker):
        client_mock = self._mock_request(mocker)

        with self.client_cls(base_url="http://localhost") as client:
            client.sync_header(bearer="Bearer test")

        assert client_mock.return_value.build_request.called
        kwargs_call = client_mock.return_value.build_request.call_args.kwargs
        assert "headers" in kwargs_call
        assert "Authorization" in kwargs_call.get("headers")
        assert kwargs_call.get("headers").get("Authorization") == "Bearer test"

    def test_optional_header(self, mocker):
        client_mock = self._mock_request(mocker)

        with self.client_cls(base_url="http://localhost") as client:
            client.sync_header()

        assert client_mock.return_value.build_request.called
        kwargs_call = client_mock.return_value.build_request.call_args.kwargs
        assert "headers" in kwargs_call
        assert "Authorization" not in kwargs_call.get("headers")

    def test_required_header(self):
        with self.client_cls(base_url="http://localhost") as client, pytest.raises(TypeError) as exc_info:
            client.sync_required_header()

        assert exc_info.value.args == ("required argument missing <bearer>",)

    def test_union_response_dict(self, mocker):
        self._mock_request(mocker, content='{"test": "test"}')

        with self.client_cls(base_url="http://localhost") as client:
            response = client.sync_union()

        assert response == {"test": "test"}

    def test_union_response_list(self, mocker):
        self._mock_request(mocker, content='[{"test": "test"}]')

        with self.client_cls(base_url="http://localhost") as client:
            response = client.sync_union()

        assert response == [{"test": "test"}]

    def test_optional_response_none(self, mocker):
        self._mock_request(mocker, content="")

        with self.client_cls(base_url="http://localhost") as client:
            response = client.sync_optional()

        assert response is None

    def test_optional_response_dict(self, mocker):
        self._mock_request(mocker, content='{"test": "test"}')

        with self.client_cls(base_url="http://localhost") as client:
            response = client.sync_optional()

        assert response == {"test": "test"}

    if sys.version_info[0] >= 3 and sys.version_info[1] > 9:

        def test_pipe_union_response_dict(self, mocker):
            self._mock_request(mocker, content='{"test": "test"}')

            with self.client_cls(base_url="http://localhost") as client:
                response = client.sync_pipe_union()

            assert response == {"test": "test"}

        def test_pipe_union_response_list(self, mocker):
            self._mock_request(mocker, content='[{"test": "test"}]')

            with self.client_cls(base_url="http://localhost") as client:
                response = client.sync_pipe_union()

            assert response == [{"test": "test"}]

        def test_pipe_optional_response_none(self, mocker):
            self._mock_request(mocker, content="")

            with self.client_cls(base_url="http://localhost") as client:
                response = client.sync_pipe_optional()

            assert response is None

        def test_pipe_optional_response_dict(self, mocker):
            self._mock_request(mocker, content='{"test": "test"}')

            with self.client_cls(base_url="http://localhost") as client:
                response = client.sync_pipe_optional()

            assert response == {"test": "test"}
