from typing import List, Optional

import httpx
import pytest
from pydantic import BaseModel
from pydantic.fields import FieldInfo

import lima_api
from lima_api.parameters import (
    BodyParameter,
    PathParameter,
    QueryParameter,
)


class Item(BaseModel):
    id: int
    name: str


class LoginDataValidate(BaseModel):
    username: str
    password: str
    client_id: str
    grant_type: str


class ItemNotFound(lima_api.LimaException): ...


class GenericError(lima_api.LimaException): ...


class AsyncClient(lima_api.LimaApi):
    @lima_api.get("/items", default_exception=GenericError)
    def sync_list(self, limit: int = FieldInfo(le=100)) -> list[Item]: ...


class SyncClient(lima_api.SyncLimaApi):
    @lima_api.get("/items", default_exception=GenericError)
    def sync_list_field_required(
        self, limit: int = FieldInfo(le=100)
    ) -> list[Item]: ...

    @lima_api.get(
        "/items",
        response_mapping={
            404: ItemNotFound,
        },
        default_exception=GenericError,
    )
    def sync_list(self, limit: int = FieldInfo(le=100, default=10)) -> list[Item]: ...

    @lima_api.post(
        "/realms/token/{path_arg}/",
        default_response_code=200,
        response_mapping={400: GenericError},
    )
    def do_login(self, path_arg: str, login: LoginDataValidate) -> None: ...

    @lima_api.post(
        "/realms/token/form",
        headers={"content-type": "application/x-www-form-urlencoded"},
        default_response_code=200,
        response_mapping={400: GenericError},
    )
    def do_login_form(self, login: LoginDataValidate) -> None: ...

    @lima_api.get("/items/query", default_exception=GenericError)
    def sync_list_query(self, limit: int = QueryParameter(le=100)) -> list[Item]: ...

    @lima_api.get("/items/body", default_exception=GenericError)
    def sync_list_body(self, limit: int = BodyParameter(le=100)) -> list[Item]: ...

    @lima_api.get("/items/{path}", default_exception=GenericError)
    def sync_list_path(
        self, limit: int = PathParameter(le=100, alias="path")
    ) -> list[Item]: ...

    @lima_api.get("/items/query_model", default_exception=GenericError)
    def sync_list_model(self, params: Item) -> list[Item]: ...

    @lima_api.get("/items/{name}/all", default_exception=GenericError)
    def sync_all_params(
        self,
        path: int = PathParameter(le=100, alias="name"),
        body: Item = BodyParameter(),
        query: int = QueryParameter(alias="name"),
    ) -> list[Item]: ...

    @lima_api.post("/items/split", default_exception=GenericError)
    def sync_list_objects(self, items: List[Item]) -> list[Item]: ...


class TestLimaApi:
    """
    TestClient
    """

    def setup_method(self):
        self.client = lima_api.LimaApi(base_url="http://localhost:8080")

    def test_init(self):
        assert self.client.base_url == "http://localhost:8080"

    def test_client_not_init_with_sync_call(self, mocker):
        client_mock = mocker.patch("httpx.Client")
        client = SyncClient(base_url="http://localhost/")

        with pytest.raises(lima_api.LimaException) as exc_info:
            client.sync_list()

        assert str(exc_info.value) == "Cliente no inicializado"
        assert not client_mock.return_value.send.called

    def test_client_field_required(self, mocker):
        client_mock = mocker.patch("httpx.Client")

        with SyncClient(base_url="http://localhost/") as client:
            with pytest.raises(TypeError) as exc_info:
                client.sync_list_field_required()

        assert str(exc_info.value) == "Falta el argumento obligatorio <limit>"
        assert not client_mock.return_value.send.called

    def test_client_init_with_sync_call(self, mocker):
        client_mock = mocker.patch("httpx.Client")
        client_mock.return_value.send.return_value.status_code = 200
        client_mock.return_value.send.return_value.content = (
            '[{"id":1, "name": "test"}]'
        )

        client = SyncClient(base_url="http://localhost/")
        client.start_client()
        response = client.sync_list()

        assert client_mock.return_value.send.called
        assert len(response) == 1
        assert response[0] == Item(id=1, name="test")

    def test_client_mapping_error_for_sync_call(self, mocker):
        client_mock = mocker.patch("httpx.Client")
        client_mock.return_value.send.return_value.status_code = 404
        client_mock.return_value.send.return_value.content = "File not found"

        with SyncClient(base_url="http://localhost/") as client:
            with pytest.raises(ItemNotFound) as exc_info:
                client.sync_list()

        assert client_mock.return_value.send.called
        assert str(exc_info.value.content) == "File not found"
        assert str(exc_info.value.status_code) == "404"
        assert str(exc_info.value.detail) == "Http Code in response_mapping"

    def test_client_generic_error_for_sync_call(self, mocker):
        client_mock = mocker.patch("httpx.Client")
        client_mock.return_value.send.return_value.status_code = 503
        client_mock.return_value.send.return_value.content = "Service Unavailable"

        with SyncClient(base_url="http://localhost/") as client:
            with pytest.raises(GenericError) as exc_info:
                client.sync_list()

        assert client_mock.return_value.send.called
        assert str(exc_info.value.content) == "Service Unavailable"
        assert str(exc_info.value.status_code) == "503"
        assert str(exc_info.value.detail) == "Http Code not in response_mapping"

    def test_warning_async_on_sync_client(self, mocker):
        client_mock = mocker.patch("httpx.Client")
        client = AsyncClient(base_url="http://localhost/")
        client.client = httpx.AsyncClient(
            transport=client.transport, timeout=client.timeout
        )

        with pytest.raises(lima_api.LimaException) as exc_info:
            client.sync_list()

        assert not client_mock.return_value.send.called
        assert str(exc_info.value.detail) == "Función síncrona en cliente asíncrono"

    def test_sync_client(self, mocker):
        client_mock = mocker.patch("httpx.Client")
        client = AsyncClient(base_url="http://localhost/")
        client.client = httpx.AsyncClient(
            transport=client.transport, timeout=client.timeout
        )

        with pytest.raises(lima_api.LimaException) as exc_info:
            client.sync_list()

        assert not client_mock.return_value.send.called
        assert str(exc_info.value.detail) == "Función síncrona en cliente asíncrono"

    def test_client_no_headers(self, mocker):
        client_mock = mocker.patch("httpx.Client")
        client_mock.return_value.send.return_value.status_code = 200
        client_mock.return_value.send.return_value.content = ""

        with SyncClient(base_url="http://localhost") as client:
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

        with SyncClient(base_url="http://localhost") as client:
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
        assert request_kwargs.get("headers") == {
            "content-type": "application/x-www-form-urlencoded"
        }
        assert "json" not in request_kwargs
        assert "data" in request_kwargs
        assert request_kwargs["data"] == {
            "username": "username",
            "password": "password",
            "client_id": "client_id",
            "grant_type": "grant_type",
        }


class TestLimaParameters:
    """
    TestClient
    """

    def setup_method(self):
        self.client = lima_api.LimaApi(base_url="http://localhost:8080")

    def test_init(self):
        assert self.client.base_url == "http://localhost:8080"

    def _mock_request(self, mocker, status_code: int = 200, content: str = "[]"):
        client_mock = mocker.patch("httpx.Client")
        client_mock.return_value.send.return_value.status_code = status_code
        client_mock.return_value.send.return_value.content = content
        return client_mock

    def test_get_params(self, mocker):
        client_mock = self._mock_request(mocker)

        with SyncClient(base_url="http://localhost") as client:
            client.sync_list_query(limit=2)

        assert client_mock.return_value.build_request.called
        method, url = client_mock.return_value.build_request.call_args.args
        assert method, url == ("GET", "http://localhost/items/query")
        request_kwargs = client_mock.return_value.build_request.call_args.kwargs
        assert "params" in request_kwargs
        assert request_kwargs["params"] == {"limit": 2}

    def test_get_body(self, mocker):
        client_mock = self._mock_request(mocker)

        with SyncClient(base_url="http://localhost") as client:
            client.sync_list_body(limit=2)

        assert client_mock.return_value.build_request.called
        method, url = client_mock.return_value.build_request.call_args.args
        assert method, url == ("GET", "http://localhost/items/body")
        request_kwargs = client_mock.return_value.build_request.call_args.kwargs
        assert "json" in request_kwargs
        assert request_kwargs["json"] == {"limit": 2}

    def test_get_path(self, mocker):
        client_mock = self._mock_request(mocker)

        with SyncClient(base_url="http://localhost") as client:
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

        with SyncClient(base_url="http://localhost") as client:
            client.sync_list_model(params=Item(id=2, name="test"))

        assert client_mock.return_value.build_request.called
        method, url = client_mock.return_value.build_request.call_args.args
        assert method, url == ("GET", "http://localhost/items/query_model")
        request_kwargs = client_mock.return_value.build_request.call_args.kwargs
        assert "params" in request_kwargs
        assert request_kwargs["params"] == {"id": 2, "name": "test"}

    def test_all_params(self, mocker):
        client_mock = self._mock_request(mocker)

        with SyncClient(base_url="http://localhost") as client:
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
                    body_1: str = BodyParameter(),
                    body_2: str = BodyParameter(),
                ) -> list[Item]: ...

        assert exc_info.value.args == ('Too many body params',)

    def test_many_body_optionals(self, mocker):
        with pytest.raises(ValueError) as exc_info:
            class SyncClient(lima_api.SyncLimaApi):
                @lima_api.get("/items/split", default_exception=GenericError)
                def sync_kwargs_overwrite_item(
                    self,
                    item: Optional[Item] = BodyParameter(default=None),
                    _id: Optional[int] = BodyParameter(default=None, alias="id"),
                    name: Optional[str] = BodyParameter(default=None),
                ) -> list[Item]: ...

        assert exc_info.value.args == ('Too many body params',)

    def test_list_objects(self, mocker):
        client_mock = self._mock_request(mocker)

        with SyncClient(base_url="http://localhost") as client:
            client.sync_list_objects(items=[Item(id=1, name="one"), Item(id=2, name="test")])

        assert client_mock.return_value.build_request.called
        method, url = client_mock.return_value.build_request.call_args.args
        assert method, url == ("GET", "http://localhost/items/query_model")
        request_kwargs = client_mock.return_value.build_request.call_args.kwargs
        assert "json" in request_kwargs
        assert request_kwargs["json"] == [{"id": 1, "name": "one"}, {"id": 2, "name": "test"}]
