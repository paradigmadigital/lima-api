from pydantic.version import VERSION

PYDANTIC_V2 = VERSION.startswith("2.")

if PYDANTIC_V2:  # pragma: no cover
    from pydantic_settings import BaseSettings
else:  # pragma: no cover
    from pydantic import BaseSettings


class LimaSettings(BaseSettings):
    lima_bracket_regex: str = r"\{(.+?)\}"
    lima_default_http_retries: int = 0
    lima_default_http_timeout: int = 15
    lima_default_response_code: int = 200
    lima_retry_after_max_retries: int = 5
    lima_retry_after_min_sleep_sec: int = 5
    lima_autologin_max_retries: int = 1


settings = LimaSettings()
