import json
import os.path
import sys
from datetime import datetime
from typing import Optional

import pytest
from client import (
    GenericError,
    Item,
    ResumeUrl,
    SyncClient,
)
from pydantic import BaseModel

import lima_api
from lima_api import LimaException
from lima_api.parameters import BodyParameter


class ExampleQuery(BaseModel):
    page: Optional[int] = None
    size: Optional[int] = None
    search: Optional[str] = None


class QueryModelDumpClient(lima_api.SyncLimaApi):
    @lima_api.get("/")
    def search_dict(
        self,
        *,
        query: ExampleQuery = lima_api.QueryParameter(model_dump_mode=lima_api.parameters.DumpMode.DICT),
        extra: str = "extra",
    ) -> None: ...

    @lima_api.get("/")
    def search_dict_none(
        self,
        *,
        query: ExampleQuery = lima_api.QueryParameter(model_dump_mode=lima_api.parameters.DumpMode.DICT_NONE),
        extra: str = "extra",
    ) -> None: ...

    @lima_api.get("/")
    def search_json(
        self,
        *,
        query: ExampleQuery = lima_api.QueryParameter(model_dump_mode=lima_api.parameters.DumpMode.JSON),
        extra: str = "extra",
    ) -> None: ...

    @lima_api.get("/")
    def search_json_none(
        self,
        *,
        query: ExampleQuery = lima_api.QueryParameter(model_dump_mode=lima_api.parameters.DumpMode.JSON_NONE),
        extra: str = "extra",
    ) -> None: ...


class TestModelDump:
    def setup_method(self):
        self.client = QueryModelDumpClient(base_url="http://localhost:8080", auto_start=True, auto_close=True)

    @pytest.mark.parametrize(
        "function_name,query,expected",
        [
            pytest.param(
                "search_dict",
                ExampleQuery(page=0, search=""),
                {"page": 0, "search": "", "extra": "extra"},
            ),
            pytest.param(
                "search_dict_none",
                ExampleQuery(page=0, search=""),
                {"page": 0, "search": "", "extra": "extra", "size": None},
            ),
        ],
    )
    def test_model_dump_mode_dict(self, mocker, function_name: str, query, expected) -> None:
        client_mock = mocker.patch("httpx.Client").return_value.__enter__
        client_mock.return_value.send.return_value.status_code = 200
        client_mock.return_value.send.return_value.content = b""
        function = getattr(self.client, function_name)
        function(query=query)

        request_kwargs = client_mock.return_value.build_request.call_args.kwargs
        assert "params" in request_kwargs
        assert request_kwargs["params"] == expected

    @pytest.mark.parametrize(
        "function_name,query,expected",
        [
            pytest.param(
                "search_json",
                ExampleQuery(page=0, search=""),
                {"page": 0, "search": ""},
            ),
            pytest.param(
                "search_json_none",
                ExampleQuery(page=0, search=""),
                {"page": 0, "size": None, "search": ""},
            ),
        ],
    )
    def test_model_dump_mode_json(self, mocker, function_name: str, query, expected) -> None:
        client_mock = mocker.patch("httpx.Client").return_value.__enter__
        client_mock.return_value.send.return_value.status_code = 200
        client_mock.return_value.send.return_value.content = b""
        function = getattr(self.client, function_name)
        function(query=query)

        request_kwargs = client_mock.return_value.build_request.call_args.kwargs
        assert "params" in request_kwargs
        assert "extra" in request_kwargs["params"]
        assert request_kwargs["params"]["extra"] == "extra"
        assert "query" in request_kwargs["params"]
        assert json.loads(request_kwargs["params"]["query"]) == expected


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
        client_mock = mocker.patch("httpx.Client").return_value.__enter__
        client_mock.return_value.send.return_value.status_code = status_code
        client_mock.return_value.send.return_value.content = content
        return client_mock

    def test_pydantic_json_dump(self, mocker):
        client_mock = self._mock_request(mocker)

        with self.client_cls(base_url="http://localhost") as client:
            client.create_new_url(
                data=ResumeUrl(
                    resume="test",
                    url="http://test.com/",
                    created=datetime(2025, 3, 15),
                )
            )

        assert client_mock.return_value.build_request.called
        method, url = client_mock.return_value.build_request.call_args.args
        assert method, url == ("POST", "http://localhost/new_url")
        request_kwargs = client_mock.return_value.build_request.call_args.kwargs
        assert "json" in request_kwargs
        assert request_kwargs["json"] == {
            "created": "2025-03-15T00:00:00",
            "resume": "test",
            "url": "http://test.com/",
        }

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

    def test_get_missing_path(self):
        with pytest.raises(LimaException) as exc_info:

            class SyncClient(lima_api.SyncLimaApi):
                @lima_api.get("/items/{missing}")
                def sync_body_split(self) -> None: ...

        assert exc_info.value.detail == "path parameters need to be defined: <missing>"

    def test_get_missing_return(self):
        with pytest.raises(TypeError) as exc_info:

            class SyncClient(lima_api.SyncLimaApi):
                @lima_api.get("/no_return")
                def sync_no_return(self): ...

        assert exc_info.value.args == ("Required return type",)

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

    def test_alias_payload(self, mocker):
        client_mock = self._mock_request(mocker)

        with self.client_cls(base_url="http://localhost") as client:
            client.sync_all_params(path=10, body=Item(id=1, name="item"), query=100)
        build_request_call = client_mock.return_value.build_request.call_args
        assert "params" in build_request_call.kwargs
        assert "name" in build_request_call.kwargs["params"]
        assert build_request_call.kwargs["params"]["name"] == 100

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
        assert "data" in request_kwargs
        assert request_kwargs["data"] == {"id": 3, "name": "name"}
        assert "files" in request_kwargs
        assert request_kwargs["files"] == {}

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

    def test_force_typing_args_with_default(self, mocker):
        with pytest.raises(TypeError) as exc_info:

            class TestSyncClient(lima_api.SyncLimaApi):
                @lima_api.get("/items/split", default_exception=GenericError)
                def sync_kwargs_no_type_but_default(self, *, first, item=BodyParameter(default=None)) -> None: ...

        assert exc_info.value.args == ("Required parameter typing for: first, item",)

    def test_force_typing_args(self, mocker):
        with pytest.raises(TypeError) as exc_info:

            class TestSyncClient(lima_api.SyncLimaApi):
                @lima_api.get("/items/split", default_exception=GenericError)
                def sync_kwargs_not_type(self, *, item: int, other) -> None: ...

        assert exc_info.value.args == ("Required parameter typing for: other",)

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

    def test_required_none_in_body_model(self, mocker):
        self._mock_request(mocker, content="")

        with (
            self.client_cls(base_url="http://localhost") as client,
            pytest.raises(lima_api.ValidationError) as exc_info,
        ):
            client.sync_required_body(item=None)
        assert exc_info.value.args == ("Invalid body",)
        errors = exc_info.value.__cause__.errors()
        assert len(errors) == 1
        error = errors[0]
        assert error["msg"] in [
            "Input should be a valid dictionary or instance of Item",
            "Item expected dict not NoneType",
        ]
        if "input" in error:
            assert error["input"] is None

    def test_required_emtpy_in_body_model(self, mocker):
        self._mock_request(mocker, content="")

        with (
            self.client_cls(base_url="http://localhost") as client,
            pytest.raises(lima_api.ValidationError) as exc_info,
        ):
            client.sync_required_body(item={})
        assert exc_info.value.args == ("Invalid body",)
        errors = exc_info.value.__cause__.errors()
        assert len(errors) == 2
        assert {error["msg"].capitalize() for error in errors} == {"Field required"}
        assert {error["loc"][0] for error in errors} == {"id", "name"}

    def test_optional_none_in_body_model(self, mocker):
        client_mock = self._mock_request(mocker, content="")

        with self.client_cls(base_url="http://localhost") as client:
            client.sync_optional_body(item=None)

        call_kwargs = client_mock.return_value.build_request.call_args.kwargs
        assert "json" in call_kwargs
        assert call_kwargs["json"] is None

    def test_optional_emtpy_in_body_model(self, mocker):
        client_mock = self._mock_request(mocker, content="")

        with self.client_cls(base_url="http://localhost") as client:
            client.sync_optional_body(item={})

        call_kwargs = client_mock.return_value.build_request.call_args.kwargs
        assert "json" in call_kwargs
        assert call_kwargs["json"] == {"id": 0, "name": ""}

    def test_none_in_query_model(self, mocker):
        client_mock = self._mock_request(mocker)

        with self.client_cls(base_url="http://localhost") as client:
            client.sync_list_model(params=None)

        call_kwargs = client_mock.return_value.build_request.call_args.kwargs
        assert "params" in call_kwargs
        assert call_kwargs["params"] == {}

    def test_emtpy_in_query_model(self, mocker):
        client_mock = self._mock_request(mocker)

        with self.client_cls(base_url="http://localhost") as client:
            client.sync_list_model(params={})

        call_kwargs = client_mock.return_value.build_request.call_args.kwargs
        assert "params" in call_kwargs
        assert call_kwargs["params"] == {"params": {}}

    def test_file_check(self, mocker):
        client_mock = self._mock_request(mocker)
        with (
            self.client_cls(base_url="http://localhost") as client,
            pytest.raises(lima_api.ValidationError) as exc_info,
        ):
            client.file_upload(file=None)

        assert not client_mock.return_value.build_request.called
        assert exc_info.value.detail == "Required parameter 'file'"

    def test_file_by_one_typing(self, mocker):
        client_mock = self._mock_request(mocker)
        with self.client_cls(base_url="http://localhost") as client, open(__file__) as f:
            client.file_one_upload(file=f)
        assert client_mock.return_value.build_request.called
        assert "files" in client_mock.return_value.build_request.call_args.kwargs
        files = client_mock.return_value.build_request.call_args.kwargs.get("files")
        assert len(files) == 1
        assert "file" in files
        assert files["file"].name == __file__

    def test_file_by_typing(self, mocker):
        client_mock = self._mock_request(mocker)
        with self.client_cls(base_url="http://localhost") as client, open(__file__) as f:
            client.file_upload(file=f)
        assert client_mock.return_value.build_request.called
        assert "files" in client_mock.return_value.build_request.call_args.kwargs
        files = client_mock.return_value.build_request.call_args.kwargs.get("files")
        assert len(files) == 1
        assert "file" in files
        assert files["file"].name == __file__

    def test_file_by_param(self, mocker):
        client_mock = self._mock_request(mocker)
        with self.client_cls(base_url="http://localhost") as client, open(__file__, "rb") as f:
            client.file_upload_param(file=(os.path.basename(__file__), f, "text/plain"))
        assert client_mock.return_value.build_request.called
        assert "files" in client_mock.return_value.build_request.call_args.kwargs
        files = client_mock.return_value.build_request.call_args.kwargs.get("files")
        assert len(files) == 1
        assert "file" in files
        (filename, fd, content_type) = files["file"]
        assert filename == os.path.basename(__file__)
        assert fd.name == __file__
        assert content_type == "text/plain"

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
        with (
            self.client_cls(base_url="http://localhost") as client,
            pytest.raises(lima_api.ValidationError) as exc_info,
        ):
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
