import sys
from typing import (
    Any,
    List,
    Optional,
    Union,
)

import lima_api
from lima_api.parameters import (
    BodyParameter,
    HeaderParameter,
    PathParameter,
    QueryParameter,
)
from pydantic import BaseModel
from pydantic.fields import FieldInfo


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


class UnexpectedError(lima_api.LimaException): ...


class AsyncClient(lima_api.LimaApi):
    @lima_api.get("/items", default_exception=GenericError)
    def sync_list(self, *, limit: int = FieldInfo(le=100)) -> list[Item]: ...


class SyncClient(lima_api.SyncLimaApi):
    @lima_api.get("/items", default_exception=UnexpectedError)
    def sync_list_field_required(self, *, limit: int = FieldInfo(le=100)) -> list[Item]: ...

    @lima_api.get(
        "/items",
        response_mapping={
            404: ItemNotFound,
        },
        default_exception=UnexpectedError,
    )
    def sync_list(self, *, limit: int = FieldInfo(le=100, default=10)) -> list[Item]: ...

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
    ) -> list[Item]: ...

    @lima_api.post("/items/split", default_exception=UnexpectedError)
    def sync_list_objects(self, *, items: list[Item]) -> list[Item]: ...

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
    def sync_list_field_required(self, *, limit: int = FieldInfo(le=100)) -> list[Item]: ...

    @lima_api.get("/items")
    def sync_list(self, *, limit: int = FieldInfo(le=100, default=10)) -> list[Item]: ...

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
