import inspect
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


class LimaApiBase:
    def __init__(
        self,
        base_url: str,
        retries: int = DEFAULT_HTTP_RETRIES,
        timeout: int = DEFAULT_HTTP_TIMEOUT,
        headers: Optional[dict[str, str]] = None,
        default_response_code: int = DEFAULT_RESPONSE_CODE,
        response_mapping: Optional[dict[int, type[LimaException]]] = None,
        undefined_values: tuple[Any, ...] = DEFAULT_UNDEFINED_VALUES,
        default_exception: type[LimaException] = LimaException,
        client_kwargs: Optional[dict] = None,
    ):
        self.base_url: str = base_url

        self.retries = retries
        self.timeout = timeout
        self.default_response_code = default_response_code
        self.default_exception = default_exception or LimaException
        if response_mapping is None:
            response_mapping = {}
        self.response_mapping: dict[int, type[LimaException]] = response_mapping
        self.undefined_values = undefined_values
        self.headers = headers
        self.transport: Optional[Union[SyncOpenTelemetryTransport, AsyncOpenTelemetryTransport]] = None
        self.client: Optional[Union[httpx.Client, httpx.AsyncClient]] = None
        self.client_kwargs = client_kwargs or {}

    def _create_request(
        self,
        sync: bool,
        method: str,
        path: str,
        path_params_mapping: dict,
        kwargs: dict,
        body_mapping: Optional[dict] = None,
        query_params_mapping: list[dict] = None,
        undefined_values: Optional[tuple[Any, ...]] = None,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> httpx.Request:
        if self.client is None:
            raise LimaException("Cliente no inicializado")

        if sync and inspect.iscoroutinefunction(self.client.send):
            raise LimaException("Función síncrona en cliente asíncrono")
        elif not sync and not inspect.iscoroutinefunction(self.client.send):
            raise LimaException("Función asíncrona en cliente síncrono")

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

        body_kwarg = {}
        if _headers.get("content-type", "application/json") == "application/json":
            body_kwarg["json"] = body
        else:
            body_kwarg["data"] = body

        api_request = self.client.build_request(
            method,
            final_url,
            params=params,
            headers=_headers,
            timeout=timeout if timeout is not None else self.timeout,
            **body_kwarg,
        )
        return api_request

    def _create_response(
        self,
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

        if api_response.status_code == (
            default_response_code if default_response_code is not None else self.default_response_code
        ):
            response = parse_data(return_class, api_response.content)
        elif api_response.status_code in mapping:
            raise mapping[api_response.status_code](
                detail="Http Code in response_mapping",
                status_code=api_response.status_code,
                content=api_response.content,
            )
        else:
            raise exp_cls(
                detail="Http Code not in response_mapping",
                status_code=api_response.status_code,
                content=api_response.content,
            )
        return response


class LimaApi(LimaApiBase):
    def __init__(
        self,
        base_url: str,
        retries: int = DEFAULT_HTTP_RETRIES,
        timeout: int = DEFAULT_HTTP_TIMEOUT,
        headers: Optional[dict[str, str]] = None,
        default_response_code: int = DEFAULT_RESPONSE_CODE,
        response_mapping: Optional[dict[int, type[LimaException]]] = None,
        undefined_values: tuple[Any, ...] = DEFAULT_UNDEFINED_VALUES,
        default_exception: type[LimaException] = LimaException,
        client_kwargs: Optional[dict] = None,
    ):
        super().__init__(
            base_url=base_url,
            retries=retries,
            timeout=timeout,
            headers=headers,
            default_response_code=default_response_code,
            response_mapping=response_mapping,
            undefined_values=undefined_values,
            default_exception=default_exception,
            client_kwargs=client_kwargs,
        )
        transport = httpx.AsyncHTTPTransport(retries=retries)
        self.transport: AsyncOpenTelemetryTransport = AsyncOpenTelemetryTransport(transport)
        self.client: Optional[httpx.AsyncClient] = None

    async def start_client(self) -> None:
        client_kwargs = self.client_kwargs.copy()
        client_kwargs["timeout"] = self.timeout
        client_kwargs["transport"] = self.transport
        self.client = httpx.AsyncClient(**self.client_kwargs)

    async def stop_client(self) -> None:
        if self.client:
            await self.client.aclose()

    async def __aenter__(self) -> "LimaApi":
        await self.start_client()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.stop_client()


class SyncLimaApi(LimaApiBase):
    def __init__(
        self,
        base_url: str,
        retries: int = DEFAULT_HTTP_RETRIES,
        timeout: int = DEFAULT_HTTP_TIMEOUT,
        headers: Optional[dict[str, str]] = None,
        default_response_code: int = DEFAULT_RESPONSE_CODE,
        response_mapping: Optional[dict[int, type[LimaException]]] = None,
        undefined_values: tuple[Any, ...] = DEFAULT_UNDEFINED_VALUES,
        default_exception: type[LimaException] = LimaException,
        client_kwargs: Optional[dict] = None,
    ):
        super().__init__(
            base_url=base_url,
            retries=retries,
            timeout=timeout,
            headers=headers,
            default_response_code=default_response_code,
            response_mapping=response_mapping,
            undefined_values=undefined_values,
            default_exception=default_exception,
            client_kwargs=client_kwargs,
        )
        transport = httpx.HTTPTransport(retries=retries)
        self.transport: SyncOpenTelemetryTransport = SyncOpenTelemetryTransport(transport)
        self.client: Optional[httpx.Client] = None

    def start_client(self) -> None:
        client_kwargs = self.client_kwargs.copy()
        client_kwargs["timeout"] = self.timeout
        client_kwargs["transport"] = self.transport
        self.client = httpx.Client(**self.client_kwargs)

    def stop_client(self) -> None:
        if self.client:
            self.client.close()

    def __enter__(self) -> "SyncLimaApi":
        self.start_client()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
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
            query_params_mapping, path_params_mapping, body_mapping = get_mappings(path, sig.parameters, method)

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
                        undefined_values=undefined_values,
                        headers=headers,
                        timeout=timeout,
                    )

                    try:
                        api_response = await self.client.send(api_request, follow_redirects=True)
                    except httpx.HTTPError as exc:
                        raise LimaException(
                            f"Problemas conectando a {exc.request.url} - {exc.__class__} - {exc}"
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

                def _func(self: LimaApi, *args: Any, **kwargs: Any) -> Any:
                    api_request = self._create_request(
                        sync=not is_async,
                        method=method,
                        path=path,
                        path_params_mapping=path_params_mapping,
                        kwargs=kwargs,
                        body_mapping=body_mapping,
                        query_params_mapping=query_params_mapping,
                        undefined_values=undefined_values,
                        headers=headers,
                        timeout=timeout,
                    )

                    try:
                        api_response = self.client.send(api_request, follow_redirects=True)
                    except httpx.HTTPError as exc:
                        raise LimaException(
                            f"Problemas conectando a {exc.request.url} - {exc.__class__} - {exc}"
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
