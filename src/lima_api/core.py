import inspect
from enum import Enum
from inspect import Signature
from typing import Any, Callable, Optional, Union

import httpx
from opentelemetry.instrumentation.httpx import (
    AsyncOpenTelemetryTransport,
    SyncOpenTelemetryTransport,
)

from .config import settings
from .exceptions import LimaException
from .utils import (
    get_body,
    get_final_url,
    get_mappings,
    get_request_params,
    parse_data,
)

DEFAULT_HTTP_RETRIES = settings.lima_default_http_retries
DEFAULT_HTTP_TIMEOUT = settings.lima_default_http_timeout
DEFAULT_RESPONSE_CODE = settings.lima_default_response_code
DEFAULT_UNDEFINED_VALUES: tuple[Any, ...] = (None, "")


class LogEvent(str, Enum):
    START_CLIENT = "start_client"
    BUILD_REQUEST = "build_request"
    SEND_REQUEST = "send_request"
    RECEIVED_RESPONSE = "received_response"
    STOP_CLIENT = "stop_client"


class LimaApiBase:
    headers: dict[str, str]
    response_mapping: dict[int, type[LimaException]]
    client_kwargs: dict
    retries: int = DEFAULT_HTTP_RETRIES
    timeout: int = DEFAULT_HTTP_TIMEOUT
    default_response_code: int = DEFAULT_RESPONSE_CODE
    undefined_values: tuple[Any, ...] = DEFAULT_UNDEFINED_VALUES
    default_exception: type[LimaException] = LimaException

    def __new__(cls, *args, **kwargs):
        new_class = super().__new__(cls)
        if not hasattr(new_class, "headers"):
            new_class.headers = {}
        if not hasattr(new_class, "response_mapping"):
            new_class.response_mapping = {}
        if not hasattr(new_class, "client_kwargs"):
            new_class.client_kwargs = {}
        return new_class

    def __init__(
        self,
        base_url: str,
        *,
        retries: Optional[int] = None,
        timeout: Optional[int] = None,
        headers: Optional[dict[str, str]] = None,
        default_response_code: Optional[int] = None,
        response_mapping: Optional[dict[int, type[LimaException]]] = None,
        undefined_values: tuple[Any, ...] = None,
        default_exception: Optional[type[LimaException]] = None,
        client_kwargs: Optional[dict] = None,
    ):
        self.base_url: str = base_url

        if retries is not None:
            self.retries = retries
        if timeout is not None:
            self.timeout = timeout
        if default_response_code is not None:
            self.default_response_code = default_response_code
        if default_exception is not None:
            self.default_exception = default_exception
        if undefined_values is not None:
            self.undefined_values = undefined_values

        self.response_mapping.update(response_mapping or {})
        self.headers.update(headers or {})
        self.transport: Optional[Union[SyncOpenTelemetryTransport, AsyncOpenTelemetryTransport]] = None
        self.client: Optional[Union[httpx.Client, httpx.AsyncClient]] = None
        self.client_kwargs.update(client_kwargs or {})

    def log(self, *, event: LogEvent, **kwargs) -> None:
        """
        Allow to customize logs inside the Lima flow.
        :param event: Where is the log "printed"
        :param kwargs: Data to be or not to be logged
        """
        ...

    def _create_request(
        self,
        *,
        sync: bool,
        method: str,
        path: str,
        path_params_mapping: dict,
        kwargs: dict,
        body_mapping: Optional[dict] = None,
        query_params_mapping: list[dict] = None,
        header_mapping: list[dict] = None,
        undefined_values: Optional[tuple[Any, ...]] = None,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> httpx.Request:
        if self.client is None:
            raise LimaException(detail="uninitialized client")

        if sync and inspect.iscoroutinefunction(self.client.send):
            raise LimaException(detail="sync function in async client")
        elif not sync and not inspect.iscoroutinefunction(self.client.send):
            raise LimaException(detail="async function in sync client")

        params = get_request_params(
            query_params_mapping,
            kwargs,
            undefined_values if undefined_values is not None else self.undefined_values,
        )

        used_params = {param["kwargs_name"] for param in path_params_mapping}
        used_params.update(param["kwargs_name"] for param in query_params_mapping)
        body_kwargs = {k: v for k, v in kwargs.items() if k not in used_params}
        body = get_body(body_mapping=body_mapping, kwargs=body_kwargs)
        final_url = get_final_url(
            url=f"{self.base_url}{path}",
            path_params_mapping=path_params_mapping,
            kwargs=kwargs,
        )
        _headers = {}
        if self.headers:
            _headers.update(self.headers)
        if headers:
            _headers.update(headers)
        for header in header_mapping:
            if header["kwargs_name"] not in kwargs and "default" not in header:
                raise TypeError(f"required argument missing <{header['kwargs_name']}>")
            header_value = kwargs.get(header.get("kwargs_name"))
            if header_value is not None:
                _headers[header.get("api_name")] = header_value

        body_kwarg = {}
        if _headers.get("content-type", "application/json") == "application/json":
            body_kwarg["json"] = body
        else:
            body_kwarg["data"] = body

        timeout = timeout if timeout is not None else self.timeout

        self.log(
            event=LogEvent.BUILD_REQUEST,
            path=path,
            method=method,
            url=final_url,
            params=params,
            headers=_headers,
            timeout=timeout,
            **body_kwarg,
        )
        api_request = self.client.build_request(
            method,
            final_url,
            params=params,
            headers=_headers,
            timeout=timeout,
            **body_kwarg,
        )
        return api_request

    def _create_response(
        self,
        *,
        api_response: httpx.Response,
        return_class: Any,
        response_mapping: Optional[dict[int, type[LimaException]]] = None,
        default_response_code: Optional[int] = None,
        default_exception: Optional[type[LimaException]] = None,
    ):
        mapping = self.response_mapping
        if response_mapping:
            mapping = self.response_mapping.copy()
            mapping.update(response_mapping)
        exp_cls = default_exception if default_exception is not None else self.default_exception

        self.log(
            event=LogEvent.RECEIVED_RESPONSE,
            response=api_response,
            response_mapping=mapping,
            return_class=return_class,
        )
        if api_response.status_code == (
            default_response_code if default_response_code is not None else self.default_response_code
        ):
            response = parse_data(return_class, api_response.content)
        elif api_response.status_code in mapping:
            ex_cls: type[LimaException] = mapping[api_response.status_code]
            raise ex_cls(
                detail=ex_cls.detail or "Http Code in response_mapping",
                status_code=api_response.status_code,
                content=api_response.content,
            )
        else:
            raise exp_cls(
                detail=exp_cls.detail or "Http Code not in response_mapping",
                status_code=api_response.status_code,
                content=api_response.content,
            )
        return response


class LimaApi(LimaApiBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        transport = httpx.AsyncHTTPTransport(retries=self.retries)
        self.transport: AsyncOpenTelemetryTransport = AsyncOpenTelemetryTransport(transport)
        self.client: Optional[httpx.AsyncClient] = None

    async def start_client(self) -> None:
        client_kwargs = self.client_kwargs.copy()
        client_kwargs["timeout"] = self.timeout
        client_kwargs["transport"] = self.transport
        client = httpx.AsyncClient(**client_kwargs)  # noqa: S113
        self.log(
            event=LogEvent.START_CLIENT,
            **client_kwargs,
        )
        self.client = await client.__aenter__()

    async def stop_client(self) -> None:
        self.log(event=LogEvent.STOP_CLIENT)
        if self.client:
            await self.client.aclose()
        self.client = None

    async def __aenter__(self) -> "LimaApi":
        await self.start_client()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self.client is not None:
            await self.client.__aexit__(exc_type, exc, tb)
        await self.stop_client()


class SyncLimaApi(LimaApiBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        transport = httpx.HTTPTransport(retries=self.retries)
        self.transport: SyncOpenTelemetryTransport = SyncOpenTelemetryTransport(transport)
        self.client: Optional[httpx.Client] = None

    def start_client(self) -> None:
        client_kwargs = self.client_kwargs.copy()
        client_kwargs["timeout"] = self.timeout
        client_kwargs["transport"] = self.transport
        client = httpx.Client(**client_kwargs)  # noqa: S113
        self.log(
            event=LogEvent.START_CLIENT,
            **client_kwargs,
        )
        self.client = client.__enter__()

    def stop_client(self) -> None:
        self.log(event=LogEvent.STOP_CLIENT)
        if self.client:
            self.client.close()
        self.client = None

    def __enter__(self) -> "SyncLimaApi":
        self.start_client()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.client is not None:
            self.client.__exit__(exc_type, exc, tb)
        self.stop_client()


OriginalFunc = Callable[[LimaApi, Any], Any]
DecoratedFunc = Callable[[LimaApi, Any], Any]


def method_factory(method):
    def http_method(
        path: str,
        timeout: Optional[int] = None,
        default_response_code: Optional[int] = None,
        response_mapping: Optional[dict[int, type[LimaException]]] = None,
        undefined_values: Optional[tuple[Any, ...]] = None,
        headers: Optional[dict[str, str]] = None,
        default_exception: Optional[type[LimaException]] = None,
    ) -> Callable:
        path = path.replace(" ", "")

        def _http_method(func: OriginalFunc) -> DecoratedFunc:
            sig: Signature = inspect.signature(func)
            return_class = sig.return_annotation
            is_async = inspect.iscoroutinefunction(func)
            (
                query_params_mapping,
                path_params_mapping,
                body_mapping,
                header_mapping,
            ) = get_mappings(path, sig.parameters, method)

            if is_async:

                async def _func(self: LimaApi, *args: Any, **kwargs: Any) -> Any:
                    api_request = self._create_request(
                        sync=not is_async,
                        method=method,
                        path=path,
                        path_params_mapping=path_params_mapping,
                        kwargs=kwargs,
                        body_mapping=body_mapping,
                        query_params_mapping=query_params_mapping,
                        header_mapping=header_mapping,
                        undefined_values=undefined_values,
                        headers=headers,
                        timeout=timeout,
                    )

                    try:
                        self.log(
                            event=LogEvent.SEND_REQUEST,
                            request=api_request,
                        )
                        api_response = await self.client.send(api_request, follow_redirects=True)
                    except httpx.HTTPError as exc:
                        raise LimaException(
                            detail=f"Connection error {exc.request.url} - {exc.__class__} - {exc}"
                        ) from exc

                    response = self._create_response(
                        api_response=api_response,
                        return_class=return_class,
                        response_mapping=response_mapping,
                        default_response_code=default_response_code,
                        default_exception=default_exception,
                    )
                    return response

            else:

                def _func(self: SyncLimaApi, *args: Any, **kwargs: Any) -> Any:
                    api_request = self._create_request(
                        sync=not is_async,
                        method=method,
                        path=path,
                        path_params_mapping=path_params_mapping,
                        kwargs=kwargs,
                        body_mapping=body_mapping,
                        query_params_mapping=query_params_mapping,
                        header_mapping=header_mapping,
                        undefined_values=undefined_values,
                        headers=headers,
                        timeout=timeout,
                    )

                    try:
                        self.log(
                            event=LogEvent.SEND_REQUEST,
                            request=api_request,
                        )
                        api_response = self.client.send(api_request, follow_redirects=True)
                    except httpx.HTTPError as exc:
                        raise LimaException(
                            detail=f"Connection error {exc.request.url} - {exc.__class__} - {exc}"
                        ) from exc

                    response = self._create_response(
                        api_response=api_response,
                        return_class=return_class,
                        response_mapping=response_mapping,
                        default_response_code=default_response_code,
                        default_exception=default_exception,
                    )
                    return response

            return _func

        return _http_method

    return http_method


get = method_factory("GET")
post = method_factory("POST")
put = method_factory("PUT")
head = method_factory("HEAD")
patch = method_factory("PATCH")
options = method_factory("OPTIONS")
delete = method_factory("DELETE")
