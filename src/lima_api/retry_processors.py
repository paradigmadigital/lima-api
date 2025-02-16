import inspect
from asyncio import sleep as async_sleep
from contextlib import suppress
from datetime import datetime, timezone
from time import sleep
from typing import Union

from lima_api import LimaException
from lima_api.config import settings
from lima_api.core import LimaApi, LimaRetryProcessor, LogEvent, SyncLimaApi


class RetryAfterProcessor(LimaRetryProcessor):
    # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Date
    HTTP_DATE = "%a, %d %b %Y %H:%M:%S %Z"
    max_retry = settings.lima_retry_after_max_retries
    min_sleep_time = settings.lima_retry_after_min_sleep_sec

    def get_sleep_seconds(self, retry_after: str) -> int:
        try:
            return int(retry_after)
        except ValueError:
            with suppress(ValueError):
                retry_at = datetime.strptime(retry_after, self.HTTP_DATE)
                return max(int((retry_at - datetime.now(tz=timezone.utc)).total_seconds()), self.min_sleep_time)
        return 0

    def do_retry(self, client: Union[LimaApi, SyncLimaApi], exception: LimaException) -> bool:
        if exception.http_response and (retry_after := exception.http_response.headers.get("Retry-After")):
            if isinstance(client, SyncLimaApi):
                sleep_seconds = self.get_sleep_seconds(retry_after)
                client.log(event=LogEvent.RETRY, retry_after=sleep_seconds)
                sleep(sleep_seconds)
            return True

        do_retry = super().do_retry(client=client, exception=exception)
        if do_retry and isinstance(client, SyncLimaApi):
            sleep(self.min_sleep_time)
        return do_retry

    async def process(self, client: LimaApi, exception: LimaException) -> bool:
        if exception.http_response and (retry_after := exception.http_response.headers.get("Retry-After")):
            sleep_seconds = self.get_sleep_seconds(retry_after)
            client.log(event=LogEvent.RETRY, retry_after=sleep_seconds)
            await async_sleep(sleep_seconds)
        else:
            await async_sleep(self.min_sleep_time)
        return True


class AutoLoginProcessor(LimaRetryProcessor):
    """
    Will call to `client.autologin() -> bool` and retry based on the result
    """

    max_retry = settings.lima_autologin_max_retries

    def do_retry(self, client: Union[LimaApi, SyncLimaApi], exception: LimaException) -> bool:
        do_retry = super().do_retry(client=client, exception=exception)
        if do_retry and hasattr(client, "autologin"):
            is_async = inspect.iscoroutinefunction(client.autologin)
            if is_async:
                return True
            return client.autologin()
        return do_retry

    async def process(self, client: LimaApi, exception: LimaException) -> bool:
        if hasattr(client, "autologin"):
            is_async = inspect.iscoroutinefunction(client.autologin)
            if is_async:
                return await client.autologin()
        return False
