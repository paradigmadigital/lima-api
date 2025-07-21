import inspect
import json
import logging
import sys
from enum import Enum
from inspect import Signature
from threading import Lock

from .constants import KwargsMode

try:
    from types import NoneType
except ImportError:  # pragma: no cover
    NoneType = type(None)
from typing import (
    Any,
    Callable,
    Optional,
    Union,
    get_args,
)

import httpx
import pydantic
from opentelemetry.instrumentation.httpx import (
    AsyncOpenTelemetryTransport,
    SyncOpenTelemetryTransport,
)

from .config import settings
from .exceptions import LimaException, ValidationError
from .utils import (
    LimaParams,
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
    """
    """
    BUILD_REQUEST = "build_request"
    """
    """
    SEND_REQUEST = "send_request"
    """
    """
    RECEIVED_RESPONSE = "received_response"
    """
    """
    STOP_CLIENT = "stop_client"
    """
    """
    SETUP = "setup"
    """
    """
    RETRY = "retry"
    """
    """


class LimaRetryProcessor:
    """
    .. versionadded:: 1.4.0
       Support for retry when exceptions are raised

    All retry processors must be instanced of `lima_api.core.LimaRetryProcessor`.

    That processors allow is adding automatic actions for your failed request,
    in order to you could fix the issue and retry.
    """
    max_retry: int = 1
    """
    Max number of retries before raise the exception.
    """

    def __init__(self):
        self.retry_count: int = 0

    def do_retry(self, client: Union["LimaApi", "SyncLimaApi"], exception: LimaException) -> bool:
        """
        Check before call process.

        Increment the `self.retry_count` counter.

        In case that False is returned `self.process` never will call
        and request will not be retried.
        """
        self.retry_count += 1
        return self.retry_count <= self.max_retry

    async def process(self, client: "LimaApi", exception: LimaException) -> bool:  # pragma: no cover
        """
        Only called in async clients.
        In sync clients process must be made on the `self.do_retry` method.

        Do the process required and return `True` if you want retry.
        """
        return True


class LimaApiBase:
    base_url: str
    """
    Base url to compose the final path.
    Will be overridden the constructor.
    """
    headers: dict[str, str]
    """
    The value of headers for httpx.Client/httpx.AsyncClient build_request function for send in each request.
    Will be updated by the constructor and/or decorator.
    """
    response_mapping: dict[Union[httpx.codes, int], type[LimaException]]
    """
    Dict with response code as key and lima exception as value.
    Will be updated by the constructor and/or decorator.
    """
    retry_mapping: dict[Union[httpx.codes, int, None], type[LimaRetryProcessor]] = {}
    """
    Mapping that define the retry processor class used depending of the http status.
    Will be updated by the decorator.
    """
    client_kwargs: dict
    """
    Dict with kwargs to pass to httpx.Client/httpx.AsyncClient
    Will be overridden the constructor.
    """
    retries: int = DEFAULT_HTTP_RETRIES
    """
    The maximum number of retries when trying to establish a connection.
    Will be updated by the constructor and/or decorator.
    """
    timeout: float = DEFAULT_HTTP_TIMEOUT
    """
    httpx.Client/httpx.AsyncClient timeout value.
    Will be updated by the constructor and/or decorator.
    """
    default_response_code: Union[httpx.codes, int] = DEFAULT_RESPONSE_CODE
    """
    Expected response code.
    Will be updated by the constructor and/or decorator.
    """
    undefined_values: tuple[Any, ...] = DEFAULT_UNDEFINED_VALUES
    """
    List of values that indicate undefined behavior
    Will be updated by the constructor and/or decorator.
    """
    default_exception: type[LimaException] = LimaException
    """
    LimaException class to raise if response code is not on response_mapping
    Will be updated by the constructor and/or decorator.
    """
    validation_exception: type[ValidationError] = ValidationError
    """
    ValidationError class to raise if response don't match with the expected model.
    """
    default_send_kwargs: dict[str, Any] = {"follow_redirects": True}
    """
    Extra kwargs send on `self.client.send` for each request.
    """

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
        base_url: Optional[str] = None,
        *,
        retries: Optional[int] = None,
        timeout: Optional[float] = None,
        headers: Optional[dict[str, str]] = None,
        default_response_code: Optional[Union[httpx.codes, int]] = None,
        response_mapping: Optional[dict[Union[httpx.codes, int], type[LimaException]]] = None,
        undefined_values: tuple[Any, ...] = None,
        default_exception: Optional[type[LimaException]] = None,
        client_kwargs: Optional[dict] = None,
        auto_start: bool = False,
    ):
        """
        :param base_url: the base URL of the client
        :param retries: the maximum number of retries when trying to establish a connection.
        :param timeout: httpx.Client/httpx.AsyncClient timeout value
        :param headers: the value of headers for httpx.Client/httpx.AsyncClient build_request function
        :param default_response_code: expected response code
        :param response_mapping: dict with response code as key and lima exception as value
        :param undefined_values: list of values that indicate undefined behavior
        :param default_exception: LimaException class to raise if response code is not on response_mapping
        :param client_kwargs: dict with kwargs to pass to httpx.Client/httpx.AsyncClient
        :param auto_start: indicate that is not required to open the connection implicitly
        """
        if base_url:
            self.base_url: str = base_url
        if not self.base_url:
            raise AttributeError("base_url is a required attribute")

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
        self._auto_start: bool = auto_start

    @property
    def auto_start(self) -> bool:
        return self._auto_start

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
        path_params_mapping: list[LimaParams],
        kwargs: dict,
        body_mapping: Optional[LimaParams] = None,
        file_mapping: Optional[list[LimaParams]] = None,
        query_params_mapping: Optional[list[LimaParams]] = None,
        header_mapping: Optional[list[LimaParams]] = None,
        undefined_values: Optional[tuple[Any, ...]] = None,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
        kwargs_mode: KwargsMode = KwargsMode.IGNORE,
    ) -> httpx.Request:
        """
        Create a `httpx` request to send.

        :param sync: if the request should be sent synchronously or asynchronously
        :param method: the method of the request
        :param path: the path of the request. It may contain path parameters.
        :param path_params_mapping: the mapping for the path parameters
        :param kwargs: the keyword arguments passed into the lima function
            that will be used to generate the proper request
        :param body_mapping: the mapping used for generate the body of the request
        :param file_mapping: the mapping used for generate the files of the request
        :param query_params_mapping: the mapping used for generate the query parameters of the request
        :param header_mapping: the mapping used for generate the headers of the request
        :param undefined_values: the values that are considered undefined
        :param headers: the headers of the request
        :param timeout: the timeout of the request
        :param kwargs_mode: how the kwargs that are not defined in the mappings are used to fill the request
        :return: an instance of `httpx.Request`
        """
        if self.client is None:
            raise LimaException(detail="uninitialized client")

        if sync and inspect.iscoroutinefunction(self.client.send):
            raise LimaException(detail="sync function in async client")
        elif not sync and not inspect.iscoroutinefunction(self.client.send):
            raise LimaException(detail="async function in sync client")

        try:
            params = get_request_params(
                query_params_mapping,
                kwargs,
                undefined_values if undefined_values is not None else self.undefined_values,
            )
        except TypeError as ex:
            validation_kwargs = {}
            if ex.args:
                validation_kwargs["detail"] = ex.args[0]
            raise self.validation_exception(**validation_kwargs) from ex

        used_params = {param["kwargs_name"] for param in path_params_mapping}
        used_params.update(param["kwargs_name"] for param in (query_params_mapping or []))
        used_params.update(file["kwargs_name"] for file in (file_mapping or []))
        body_kwargs = {k: v for k, v in kwargs.items() if k not in used_params}
        try:
            body = get_body(body_mapping=body_mapping, kwargs=body_kwargs)
            if kwargs_mode == KwargsMode.BODY:
                if body is None:
                    body = body_kwargs
                elif isinstance(body, dict):
                    body.update(
                        {k: v for k, v in body_kwargs.items() if k not in body and k not in body_mapping["kwargs_name"]}
                    )
            elif kwargs_mode == KwargsMode.QUERY:
                params.update(
                    {k: v for k, v in body_kwargs.items() if not body_mapping or k not in body_mapping["kwargs_name"]}
                )
        except pydantic.ValidationError as ex:
            raise self.validation_exception("Invalid body") from ex
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
        for header in header_mapping or []:
            if header["kwargs_name"] not in kwargs and "default" not in header:
                raise self.validation_exception(f"required argument missing <{header['kwargs_name']}>")
            header_value = kwargs.get(header.get("kwargs_name"))
            if header_value is not None:
                _headers[header.get("api_name")] = header_value

        files = None
        if file_mapping:
            files = {}
            for file_map in file_mapping:
                f = kwargs.get(file_map.get("kwargs_name"))
                if f is None:
                    if NoneType not in get_args(file_map.get("wrap")):
                        raise ValidationError(f"Required parameter '{file_map.get('kwargs_name')}'")
                else:
                    files[file_map.get("api_name")] = f

        body_kwarg = {}
        if _headers.get("content-type", "application/json") == "application/json" and not file_mapping:
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
            files=files,
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
        response_mapping: Optional[dict[Union[httpx.codes, int], type[LimaException]]] = None,
        default_response_code: Optional[Union[httpx.codes, int]] = None,
        default_exception: Optional[type[LimaException]] = None,
    ) -> Any:
        """
        Create a response object from an httpx.Response

        :param api_response: httpx.Response object
        :param return_class: class of the response object
        :param response_mapping: dict with response code as key and lima exception as value
        :param default_response_code: expected response code
        :param default_exception: LimaException class to raise if response code is not on response_mapping
        :return: response object
        :raises LimaException: if response code is not on response_mapping or if the response body could not be parsed
        """
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
            try:
                response = parse_data(return_class, api_response.content)
            except (pydantic.ValidationError, json.JSONDecodeError) as ex:
                raise self.validation_exception(
                    status_code=api_response.status_code,
                    content=api_response.content,
                    request=api_response.request,
                    response=api_response,
                ) from ex
        elif api_response.status_code in mapping:
            ex_cls: type[LimaException] = mapping[api_response.status_code]
            raise ex_cls(
                detail=ex_cls.detail or f"Http Code {api_response.status_code} in response_mapping",
                status_code=api_response.status_code,
                content=api_response.content,
                request=api_response.request,
                response=api_response,
            )
        else:
            raise exp_cls(
                detail=exp_cls.detail or f"Http Code {api_response.status_code} not in response_mapping",
                status_code=api_response.status_code,
                content=api_response.content,
                request=api_response.request,
                response=api_response,
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

    async def make_request(
        self,
        sync: bool,
        method: str,
        path: str,
        path_params_mapping: list[LimaParams],
        kwargs: dict,
        return_class: Any,
        body_mapping: Optional[LimaParams] = None,
        file_mapping: Optional[list[LimaParams]] = None,
        query_params_mapping: Optional[list[LimaParams]] = None,
        header_mapping: Optional[list[LimaParams]] = None,
        undefined_values: Optional[tuple[Any, ...]] = None,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
        response_mapping: Optional[dict[Union[httpx.codes, int], type[LimaException]]] = None,
        default_response_code: Optional[Union[httpx.codes, int]] = None,
        default_exception: Optional[type[LimaException]] = None,
        send_kwargs: Optional[dict] = None,
        retry_mapping: Optional[dict[Union[httpx.codes, int, None], type[LimaRetryProcessor]]] = None,
        kwargs_mode: KwargsMode = KwargsMode.IGNORE,
    ) -> Any:
        """
        Make a request to the server.

        This method will make a request to the server and return the response.
        It will handle the retry logic according to the retry mapping.

        :param sync: if the request should be sent synchronously or asynchronously
        :param method: the method of the request
        :param path: the path of the request. It may contain path parameters.
        :param path_params_mapping: the mapping for the path parameters
        :param kwargs: the keyword arguments of the function that will be used to generate the proper request
        :param return_class: the class that will be used to create the response object
        :param body_mapping: the mapping used for generate the body of the request
        :param file_mapping: the mapping used for generate the files of the request
        :param query_params_mapping: the mapping used for generate the query parameters of the request
        :param header_mapping: the mapping used for generate the headers of the request
        :param undefined_values: the values that are considered undefined
        :param headers: the headers of the request
        :param timeout: the timeout of the request
        :param response_mapping: the mapping used to know which exception to raise for each status code
        :param default_response_code: the default status code to use when the status code is not in the response mapping
        :param default_exception: the default exception to raise when the status code is not in the response mapping
        :param send_kwargs: the keyword arguments passed into the `client.send` method
        :param retry_mapping: the mapping used to know which retry processor to use for each status code
        :param kwargs_mode: how the kwargs that are not defined in the mappings are used to fill the request
        :return: the response object
        """
        do_request = True
        if retry_mapping is None:
            retry_mapping = {}
        retry_objects: dict[Union[httpx.codes, int, None], LimaRetryProcessor] = {}
        while do_request:
            try:
                response = await self._request(
                    sync=sync,
                    method=method,
                    path=path,
                    path_params_mapping=path_params_mapping,
                    kwargs=kwargs,
                    return_class=return_class,
                    body_mapping=body_mapping,
                    file_mapping=file_mapping,
                    query_params_mapping=query_params_mapping,
                    header_mapping=header_mapping,
                    undefined_values=undefined_values,
                    headers=headers,
                    timeout=timeout,
                    response_mapping=response_mapping,
                    default_response_code=default_response_code,
                    default_exception=default_exception,
                    send_kwargs=send_kwargs,
                    kwargs_mode=kwargs_mode,
                )
                return response
            except LimaException as ex:
                do_request = False
                retry_cls = None
                if ex.status_code in retry_mapping:
                    retry_cls = retry_mapping[ex.status_code]
                elif ex.status_code in self.retry_mapping:
                    retry_cls = self.retry_mapping[ex.status_code]
                if retry_cls:
                    if ex.status_code not in retry_objects:
                        retry_protocol = retry_cls()
                        retry_objects[ex.status_code] = retry_protocol
                    do_request = retry_objects[ex.status_code].do_retry(self, ex)
                    if do_request:
                        do_request = await retry_objects[ex.status_code].process(self, ex)

                if not do_request:
                    raise ex

    async def _request(
        self,
        sync: bool,
        method: str,
        path: str,
        path_params_mapping: list[LimaParams],
        kwargs: dict,
        return_class: Any,
        body_mapping: Optional[LimaParams] = None,
        file_mapping: Optional[list[LimaParams]] = None,
        query_params_mapping: Optional[list[LimaParams]] = None,
        header_mapping: Optional[list[LimaParams]] = None,
        undefined_values: Optional[tuple[Any, ...]] = None,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
        response_mapping: Optional[dict[Union[httpx.codes, int], type[LimaException]]] = None,
        default_response_code: Optional[Union[httpx.codes, int]] = None,
        default_exception: Optional[type[LimaException]] = None,
        send_kwargs: Optional[dict] = None,
        kwargs_mode: KwargsMode = KwargsMode.IGNORE,
    ) -> Any:
        """
        Send an HTTP request and return the response.

        This method constructs an HTTP request using the provided parameters,
        sends it, and processes the response. It handles automatic retries and exceptions.

        :param sync: Whether the request should be sent synchronously or asynchronously.
        :param method: The HTTP method to use for the request (e.g., 'GET', 'POST').
        :param path: The URL path for the request, which may include path parameters.
        :param path_params_mapping: Mapping for path parameters used in the request URL.
        :param kwargs: Additional keyword arguments for constructing the request.
        :param return_class: The class type to use for the response object.
        :param body_mapping: Mapping used to generate the request body.
        :param file_mapping: Mapping used to generate files for the request.
        :param query_params_mapping: Mapping used to generate query parameters.
        :param header_mapping: Mapping used to generate request headers.
        :param undefined_values: Values considered undefined and to be ignored.
        :param headers: Additional headers for the request.
        :param timeout: Timeout for the request in seconds.
        :param response_mapping: Mapping to determine which exception to raise for each status code.
        :param default_response_code: Default status code expected in the response.
        :param default_exception: Default exception to raise if the status code is not in the mapping.
        :param send_kwargs: Additional keyword arguments for the `client.send` method.
        :param kwargs_mode: Specifies how undefined kwargs are processed.
        :return: An instance of the response class specified by `return_class`.
        :raises LimaException: If there is a connection error or if the response code
                               is not in the response mapping.
        """
        if send_kwargs is None:
            send_kwargs = self.default_send_kwargs

        auto_close = False
        if self.auto_start and (self.client is None or self.client.is_closed):
            auto_close = True
            await self.__aenter__()

        api_request = None
        api_response = None
        try:
            api_request = self._create_request(
                sync=sync,
                method=method,
                path=path,
                path_params_mapping=path_params_mapping,
                kwargs=kwargs,
                body_mapping=body_mapping,
                file_mapping=file_mapping,
                query_params_mapping=query_params_mapping,
                header_mapping=header_mapping,
                undefined_values=undefined_values,
                headers=headers,
                timeout=timeout,
                kwargs_mode=kwargs_mode,
            )

            self.log(
                event=LogEvent.SEND_REQUEST,
                request=api_request,
            )
            api_response = await self.client.send(api_request, **send_kwargs)
        except httpx.HTTPError as exc:
            url = api_request.url if api_request else f"{self.base_url}{path}"
            raise LimaException(
                detail=f"Connection error {url} - {exc.__class__} - {exc}",
                request=api_request,
                response=api_response,
            ) from exc
        finally:
            if auto_close:
                await self.__aexit__(*sys.exc_info())

        response = self._create_response(
            api_response=api_response,
            return_class=return_class,
            response_mapping=response_mapping,
            default_response_code=default_response_code,
            default_exception=default_exception,
        )
        return response


class SyncLimaApi(LimaApiBase):
    def __init__(self, *args, auto_close: bool = True, **kwargs):
        self._auto_close: bool = auto_close and kwargs.get("auto_start", False)
        super().__init__(*args, **kwargs)
        transport = httpx.HTTPTransport(retries=self.retries)
        self.transport: SyncOpenTelemetryTransport = SyncOpenTelemetryTransport(transport)
        self.client: Optional[httpx.Client] = None
        self._lock = Lock()
        self._open_connections = 0

    def __del__(self):
        if self.client:
            self.__exit__(None, None, None)

    @property
    def auto_close(self) -> bool:
        if self._auto_close and not self.auto_start:
            msg = "auto_close not allowed with auto_start=False, setting off"
            logging.warning(msg)
            self.log(event=LogEvent.SETUP, msg=msg)
            self._auto_close = False
        return self._auto_close

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

    def make_request(
        self,
        sync: bool,
        method: str,
        path: str,
        path_params_mapping: list[LimaParams],
        kwargs: dict,
        return_class: Any,
        body_mapping: Optional[LimaParams] = None,
        file_mapping: Optional[list[LimaParams]] = None,
        query_params_mapping: Optional[list[LimaParams]] = None,
        header_mapping: Optional[list[LimaParams]] = None,
        undefined_values: Optional[tuple[Any, ...]] = None,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
        response_mapping: Optional[dict[Union[httpx.codes, int], type[LimaException]]] = None,
        default_response_code: Optional[Union[httpx.codes, int]] = None,
        default_exception: Optional[type[LimaException]] = None,
        send_kwargs: Optional[dict] = None,
        retry_mapping: Optional[dict[Union[httpx.codes, int, None], type[LimaRetryProcessor]]] = None,
        kwargs_mode: KwargsMode = KwargsMode.IGNORE,
    ) -> Any:
        """
        Make a request to the server.

        This method will make a request to the server and return the response.
        It will handle the retry logic according to the retry mapping.

        :param sync: if the request should be sent synchronously or asynchronously
        :param method: the method of the request
        :param path: the path of the request. It may contain path parameters.
        :param path_params_mapping: the mapping for the path parameters
        :param kwargs: the keyword arguments of the function that will be used to generate the proper request
        :param return_class: the class that will be used to create the response object
        :param body_mapping: the mapping used for generate the body of the request
        :param file_mapping: the mapping used for generate the files of the request
        :param query_params_mapping: the mapping used for generate the query parameters of the request
        :param header_mapping: the mapping used for generate the headers of the request
        :param undefined_values: the values that are considered undefined
        :param headers: the headers of the request
        :param timeout: the timeout of the request
        :param response_mapping: the mapping used to know which exception to raise for each status code
        :param default_response_code: the default status code to use when the status code is not in the response mapping
        :param default_exception: the default exception to raise when the status code is not in the response mapping
        :param send_kwargs: the keyword arguments passed into the `client.send` method
        :param retry_mapping: the mapping used to know which retry processor to use for each status code
        :param kwargs_mode: how the kwargs that are not defined in the mappings are used to fill the request
        :return: the response object
        """
        do_request = True
        if retry_mapping is None:
            retry_mapping = {}
        retry_objects: dict[Union[httpx.codes, int, None], LimaRetryProcessor] = {}
        while do_request:
            try:
                response = self._request(
                    sync=sync,
                    method=method,
                    path=path,
                    path_params_mapping=path_params_mapping,
                    kwargs=kwargs,
                    return_class=return_class,
                    body_mapping=body_mapping,
                    file_mapping=file_mapping,
                    query_params_mapping=query_params_mapping,
                    header_mapping=header_mapping,
                    undefined_values=undefined_values,
                    headers=headers,
                    timeout=timeout,
                    response_mapping=response_mapping,
                    default_response_code=default_response_code,
                    default_exception=default_exception,
                    send_kwargs=send_kwargs,
                    kwargs_mode=kwargs_mode,
                )
                return response
            except LimaException as ex:
                do_request = False
                retry_cls = None
                if ex.status_code in retry_mapping:
                    retry_cls = retry_mapping[ex.status_code]
                elif ex.status_code in self.retry_mapping:
                    retry_cls = self.retry_mapping[ex.status_code]
                if retry_cls:
                    if ex.status_code not in retry_objects:
                        retry_protocol = retry_cls()
                        retry_objects[ex.status_code] = retry_protocol
                    do_request = retry_objects[ex.status_code].do_retry(self, ex)

                if not do_request:
                    raise ex

    def _request(
        self,
        sync: bool,
        method: str,
        path: str,
        path_params_mapping: list[LimaParams],
        kwargs: dict,
        return_class: Any,
        body_mapping: Optional[LimaParams] = None,
        file_mapping: Optional[list[LimaParams]] = None,
        query_params_mapping: Optional[list[LimaParams]] = None,
        header_mapping: Optional[list[LimaParams]] = None,
        undefined_values: Optional[tuple[Any, ...]] = None,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
        response_mapping: Optional[dict[Union[httpx.codes, int], type[LimaException]]] = None,
        default_response_code: Optional[Union[httpx.codes, int]] = None,
        default_exception: Optional[type[LimaException]] = None,
        send_kwargs: Optional[dict] = None,
        kwargs_mode: KwargsMode = KwargsMode.IGNORE,
    ) -> Any:
        """
        Send an HTTP request and return the response.

        This method constructs an HTTP request using the provided parameters,
        sends it, and processes the response. It handles automatic retries and exceptions.

        :param sync: Whether the request should be sent synchronously or asynchronously.
        :param method: The HTTP method to use for the request (e.g., 'GET', 'POST').
        :param path: The URL path for the request, which may include path parameters.
        :param path_params_mapping: Mapping for path parameters used in the request URL.
        :param kwargs: Additional keyword arguments for constructing the request.
        :param return_class: The class type to use for the response object.
        :param body_mapping: Mapping used to generate the request body.
        :param file_mapping: Mapping used to generate files for the request.
        :param query_params_mapping: Mapping used to generate query parameters.
        :param header_mapping: Mapping used to generate request headers.
        :param undefined_values: Values considered undefined and to be ignored.
        :param headers: Additional headers for the request.
        :param timeout: Timeout for the request in seconds.
        :param response_mapping: Mapping to determine which exception to raise for each status code.
        :param default_response_code: Default status code expected in the response.
        :param default_exception: Default exception to raise if the status code is not in the mapping.
        :param send_kwargs: Additional keyword arguments for the `client.send` method.
        :param kwargs_mode: Specifies how undefined kwargs are processed.
        :return: An instance of the response class specified by `return_class`.
        :raises LimaException: If there is a connection error or if the response code
                               is not in the response mapping.
        """
        if send_kwargs is None:
            send_kwargs = self.default_send_kwargs
        if self.auto_close:
            with self._lock:
                self._open_connections += 1

        api_request = None
        api_response = None
        try:
            if self.auto_start and (self.client is None or self.client.is_closed):
                self.__enter__()

            api_request = self._create_request(
                sync=sync,
                method=method,
                path=path,
                path_params_mapping=path_params_mapping,
                kwargs=kwargs,
                body_mapping=body_mapping,
                file_mapping=file_mapping,
                query_params_mapping=query_params_mapping,
                header_mapping=header_mapping,
                undefined_values=undefined_values,
                headers=headers,
                timeout=timeout,
                kwargs_mode=kwargs_mode,
            )

            self.log(
                event=LogEvent.SEND_REQUEST,
                request=api_request,
            )
            api_response = self.client.send(api_request, **send_kwargs)
        except httpx.HTTPError as exc:
            url = api_request.url if api_request else f"{self.base_url}{path}"
            raise LimaException(
                detail=f"Connection error {url} - {exc.__class__} - {exc}",
                request=api_request,
                response=api_response,
            ) from exc
        finally:
            if self.auto_close:
                with self._lock:
                    self._open_connections -= 1
                    if not bool(self._open_connections):
                        self.__exit__(*sys.exc_info())

        response = self._create_response(
            api_response=api_response,
            return_class=return_class,
            response_mapping=response_mapping,
            default_response_code=default_response_code,
            default_exception=default_exception,
        )
        return response


OriginalFunc = Callable[[LimaApi, Any], Any]
DecoratedFunc = Callable[[LimaApi, Any], Any]


def method_factory(method):
    def http_method(
        path: str,
        timeout: Optional[float] = None,
        default_response_code: Optional[Union[httpx.codes, int]] = None,
        response_mapping: Optional[dict[Union[httpx.codes, int], type[LimaException]]] = None,
        undefined_values: Optional[tuple[Any, ...]] = None,
        headers: Optional[dict[str, str]] = None,
        default_exception: Optional[type[LimaException]] = None,
        retry_mapping: Optional[dict[Union[httpx.codes, int, None], type[LimaRetryProcessor]]] = None,
        kwargs_mode: KwargsMode = KwargsMode.IGNORE,
    ) -> Callable:
        """
        :param path: The URL path for the request, which may include path parameters.
        :param timeout: Timeout for the request in seconds.
        :param default_response_code: Default status code expected in the response.
        :param response_mapping: Mapping to determine which exception to raise for each status code.
        :param default_response_code: Default status code expected in the response.
        :param headers: Additional headers for the request.
        :param default_exception: Default exception to raise if the status code is not in the mapping.
        :param retry_mapping: the mapping used to know which retry processor to use for each status code
        :param kwargs_mode: Specifies how undefined kwargs are processed.
        :return: An instance of the response class specified by function.
        """
        path = path.replace(" ", "")

        if method == "GET" and kwargs_mode != KwargsMode.IGNORE:
            kwargs_mode = KwargsMode.QUERY

        def _http_method(func: OriginalFunc) -> DecoratedFunc:
            sig: Signature = inspect.signature(func)
            return_class = sig.return_annotation
            if return_class is inspect.Signature.empty:
                raise TypeError("Required return type")
            is_async = inspect.iscoroutinefunction(func)
            (
                query_params_mapping,
                path_params_mapping,
                body_mapping,
                header_mapping,
                file_mapping,
            ) = get_mappings(path, sig.parameters, method)

            if is_async:

                async def _func(self: LimaApi, *args: Any, **kwargs: Any) -> Any:
                    return await self.make_request(
                        not is_async,
                        method,
                        path,
                        path_params_mapping,
                        kwargs,
                        return_class,
                        body_mapping=body_mapping,
                        query_params_mapping=query_params_mapping,
                        file_mapping=file_mapping,
                        header_mapping=header_mapping,
                        undefined_values=undefined_values,
                        headers=headers,
                        timeout=timeout,
                        response_mapping=response_mapping,
                        default_response_code=default_response_code,
                        default_exception=default_exception,
                        retry_mapping=retry_mapping,
                        kwargs_mode=kwargs_mode,
                    )
            else:

                def _func(self: SyncLimaApi, *args: Any, **kwargs: Any) -> Any:
                    if not hasattr(self, "_lock"):
                        raise LimaException(detail="sync function in async client")

                    return self.make_request(
                        not is_async,
                        method,
                        path,
                        path_params_mapping,
                        kwargs,
                        return_class,
                        body_mapping=body_mapping,
                        query_params_mapping=query_params_mapping,
                        file_mapping=file_mapping,
                        header_mapping=header_mapping,
                        undefined_values=undefined_values,
                        headers=headers,
                        timeout=timeout,
                        response_mapping=response_mapping,
                        default_response_code=default_response_code,
                        default_exception=default_exception,
                        retry_mapping=retry_mapping,
                        kwargs_mode=kwargs_mode,
                    )

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
