import sys
from datetime import datetime
from typing import (
    IO,
    Any,
    BinaryIO,
    List,
    Optional,
    TextIO,
    Union,
)

import httpx
from httpx._types import FileTypes
from pydantic import BaseModel, HttpUrl
from pydantic.fields import Field

import lima_api
from lima_api.parameters import (
    BodyParameter,
    HeaderParameter,
    PathParameter,
    QueryParameter,
)
from lima_api.retry_processors import AutoLoginProcessor, RetryAfterProcessor


class Item(BaseModel):
    id: int
    name: str


class OptionalItem(BaseModel):
    id: int = 0
    name: str = Field(default="")


class ResumeUrl(BaseModel):
    resume: str = 0
    url: HttpUrl
    created: datetime


class LoginDataValidate(BaseModel):
    username: str
    password: str
    client_id: str
    grant_type: str


class ItemNotFound(lima_api.LimaException): ...


class GenericError(lima_api.LimaException): ...


class TooManyRequestError(lima_api.LimaException): ...


class UnexpectedError(lima_api.LimaException): ...


class AsyncClient(lima_api.LimaApi):
    retry_mapping = {httpx.codes.UNAUTHORIZED: AutoLoginProcessor}

    @lima_api.get("/items", default_exception=GenericError)
    def sync_list(self, *, limit: int = lima_api.QueryParameter(le=100)) -> list[Item]: ...

    @lima_api.get(
        "/items",
        response_mapping={
            429: TooManyRequestError,
        },
        default_exception=GenericError,
        retry_mapping={httpx.codes.TOO_MANY_REQUESTS: RetryAfterProcessor},
    )
    async def async_list(self, *, limit: int = lima_api.QueryParameter(default=100)) -> list[Item]: ...


class KwargsSyncClient(lima_api.SyncLimaApi):
    @lima_api.get("/")
    def get_exclude_kwargs(self, **kwargs) -> None: ...

    @lima_api.get("/", kwargs_mode="query")
    def get_send_query_kwargs(self, **kwargs) -> None: ...

    @lima_api.get("/", kwargs_mode="body")
    def get_send_body_kwargs(self, **kwargs) -> None: ...

    @lima_api.post("/")
    def post_exclude_kwargs(self, **kwargs) -> None: ...

    @lima_api.post("/", kwargs_mode="query")
    def post_send_query_kwargs(self, **kwargs) -> None: ...

    @lima_api.post("/", kwargs_mode="body")
    def post_send_json_kwargs(self, **kwargs) -> None: ...

    @lima_api.post(
        "/",
        headers={"content-type": "application/x-www-form-urlencoded"},
        kwargs_mode="body",
    )
    def post_send_body_kwargs(self, **kwargs) -> None: ...

    @lima_api.post("/", kwargs_mode="query")
    def post_send_query_kwargs_with_args(
        self,
        *,
        query: str = lima_api.QueryParameter(default="test"),
        **kwargs,
    ) -> None: ...

    @lima_api.post("/", kwargs_mode="query")
    def post_send_query_kwargs_with_model_args(
        self,
        *,
        body: Item,
        query: str = lima_api.QueryParameter(default="test"),
        **kwargs,
    ) -> None: ...

    @lima_api.post("/", kwargs_mode="body")
    def post_send_body_kwargs_with_model_args(
        self,
        *,
        body: Item,
        query: str = lima_api.QueryParameter(default="test"),
        **kwargs,
    ) -> None: ...


class SyncClient(lima_api.SyncLimaApi):
    retry_mapping = {httpx.codes.UNAUTHORIZED: AutoLoginProcessor}

    @lima_api.get("/items", default_exception=UnexpectedError)
    def sync_list_field_required(self, *, limit: int = QueryParameter(le=100)) -> list[Item]: ...

    @lima_api.get(
        "/items",
        response_mapping={
            404: ItemNotFound,
            429: TooManyRequestError,
        },
        default_exception=UnexpectedError,
        retry_mapping={httpx.codes.TOO_MANY_REQUESTS: RetryAfterProcessor},
    )
    def sync_list(self, *, limit: int = QueryParameter(le=100, default=10)) -> list[Item]: ...

    @lima_api.post(
        "/realms/token/{path_arg}/",
        default_response_code=200,
        response_mapping={400: GenericError},
    )
    def do_login(self, *, path_arg: str, login: LoginDataValidate) -> None: ...

    @lima_api.post(
        "/realms/token/form",
        headers={"content-type": "application/x-www-form-urlencoded"},
        default_response_code=200,
        response_mapping={400: GenericError},
    )
    def do_login_form(self, *, login: LoginDataValidate) -> None: ...

    @lima_api.get("/bytes")
    def sync_get_bytes(self) -> bytes: ...

    @lima_api.get("/any")
    def sync_get_any(self) -> Any: ...

    @lima_api.get("/items/query", default_exception=UnexpectedError)
    def sync_list_query(self, *, limit: int = QueryParameter(le=100)) -> list[Item]: ...

    @lima_api.get("/items/body", default_exception=UnexpectedError)
    def sync_list_body(self, *, limit: int = BodyParameter(le=100)) -> list[Item]: ...

    @lima_api.get("/items/{path}", default_exception=UnexpectedError)
    def sync_list_path(self, *, limit: int = PathParameter(le=100, alias="path")) -> list[Item]: ...

    @lima_api.get("/items/query_model", default_exception=UnexpectedError)
    def sync_list_model(self, *, params: Item) -> list[Item]: ...

    @lima_api.get("/items/{name}/all", default_exception=UnexpectedError)
    def sync_all_params(
        self,
        *,
        path: int = PathParameter(le=100, alias="name"),
        body: Item = BodyParameter(),
        query: int = QueryParameter(alias="name"),
        file: Optional[FileTypes] = lima_api.FileParameter(default=None),
    ) -> list[Item]: ...

    @lima_api.post("/items/test")
    def sync_required_body(self, *, item: Item) -> list[Item]: ...

    @lima_api.post("/items/test")
    def sync_optional_body(self, *, item: Optional[OptionalItem]) -> None: ...

    @lima_api.post("/one_file")
    def file_one_upload(self, *, file: IO) -> None: ...

    @lima_api.post("/file")
    def file_upload(self, *, file: Union[IO, TextIO, BinaryIO]) -> None: ...

    @lima_api.post("/file_upload")
    def file_upload_param(self, *, file: FileTypes = lima_api.FileParameter()) -> None: ...

    @lima_api.post("/items/split", default_exception=UnexpectedError)
    def sync_list_objects(self, *, items: list[Item]) -> None: ...

    @lima_api.post("/items/typing", default_exception=UnexpectedError)
    def sync_list_typing_objects(self, *, items: List[Item]) -> List[Item]: ...

    @lima_api.post("/me")
    def sync_header(self, *, bearer: str = HeaderParameter(alias="Authorization", default=None)) -> None: ...

    @lima_api.post("/me")
    def sync_required_header(self, *, bearer: str = HeaderParameter(alias="Authorization")) -> None: ...

    @lima_api.post("/union")
    def sync_union(self) -> Union[list, dict]: ...

    @lima_api.post("/optional")
    def sync_optional(self) -> Optional[dict]: ...

    @lima_api.get("/async_on_sync")
    async def async_on_sync(self) -> Optional[dict]: ...

    @lima_api.post("/new_url")
    def create_new_url(self, *, data: ResumeUrl) -> None: ...

    if sys.version_info[0] >= 3 and sys.version_info[1] > 9:

        @lima_api.post("/union")
        def sync_pipe_union(self) -> list | dict: ...

        @lima_api.post("/optional")
        def sync_pipe_optional(self) -> dict | None: ...


class SyncDeclarativeConfClient(lima_api.SyncLimaApi):
    default_response_code = 200
    default_exception = UnexpectedError
    response_mapping = {
        404: ItemNotFound,
        400: GenericError,
    }

    @lima_api.get("/items")
    def sync_list_field_required(self, *, limit: int = QueryParameter(le=100)) -> list[Item]: ...

    @lima_api.get("/items")
    def sync_list(self, *, limit: int = QueryParameter(le=100, default=10)) -> list[Item]: ...

    @lima_api.post("/realms/token/{path_arg}/")
    def do_login(self, *, path_arg: str, login: LoginDataValidate) -> None: ...

    @lima_api.post(
        "/realms/token/form",
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    def do_login_form(self, *, login: LoginDataValidate) -> None: ...

    @lima_api.get("/items/query")
    def sync_list_query(self, *, limit: int = QueryParameter(le=100)) -> list[Item]: ...

    @lima_api.get("/items/body")
    def sync_list_body(self, *, limit: int = BodyParameter(le=100)) -> list[Item]: ...

    @lima_api.get("/items/{path}")
    def sync_list_path(self, *, limit: int = PathParameter(le=100, alias="path")) -> list[Item]: ...

    @lima_api.get("/items/query_model")
    def sync_list_model(self, *, params: Item) -> list[Item]: ...

    @lima_api.get("/items/{name}/all")
    def sync_all_params(
        self,
        *,
        path: int = PathParameter(le=100, alias="name"),
        body: Item = BodyParameter(),
        query: int = QueryParameter(alias="name"),
    ) -> list[Item]: ...

    @lima_api.post("/items/split")
    def sync_list_objects(self, *, items: list[Item]) -> list[Item]: ...

    @lima_api.post("/items/typing")
    def sync_list_typing_objects(self, *, items: List[Item]) -> List[Item]: ...  #

    @lima_api.get("/bytes")
    def sync_get_bytes(self) -> bytes: ...

    @lima_api.get("/any")
    def sync_get_any(self) -> Any: ...
