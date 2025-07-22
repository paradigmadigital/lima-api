from pydantic.version import VERSION

PYDANTIC_V2 = VERSION.startswith("2.")

if PYDANTIC_V2:  # pragma: no cover
    from pydantic_settings import BaseSettings
else:  # pragma: no cover
    from pydantic import BaseSettings


class LimaSettings(BaseSettings):
    lima_bracket_regex: str = r"\{(.+?)\}"
    """
    .. versionadded:: 0.1.0

    Regex expression that will get the names in the path params and
    macht the param names defined in the function.
    """
    lima_default_http_retries: int = 0
    """
    .. versionadded:: 0.1.0

    Number of retries used to
    `httpx.HTTPTransport or httpx.AsyncHTTPTransport <https://www.python-httpx.org/advanced/transports/>`_
    """
    lima_default_http_timeout: float = 15
    """
    .. versionadded:: 0.1.0

    .. versionchanged:: 1.4.2
       Typing changed from int to float

    Number of seconds used in timeout parameter of `httpx.Client or httpx.AsyncClient <https://www.python-httpx.org/advanced/timeouts/>`_
    """
    lima_default_response_code: int = 200
    """
    .. versionadded:: 0.1.0

    Default expected response http code
    """
    lima_retry_after_max_retries: int = 5
    """
    .. versionadded:: 1.4.0
    """
    lima_retry_after_min_sleep_sec: int = 5
    """
    .. versionadded:: 1.4.0
    """
    lima_autologin_max_retries: int = 1
    """
    .. versionadded:: 1.4.0
    """


settings = LimaSettings()
