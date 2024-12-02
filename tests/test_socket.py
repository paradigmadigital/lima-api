import json
from concurrent.futures import ThreadPoolExecutor
from time import sleep

from client import SyncClient
from pytest_httpserver import HTTPServer
from werkzeug.wrappers import Request, Response


class MockSyncClient(SyncClient):
    def __init__(self, *args, **kwargs):
        self.close_counter = 0
        super().__init__(*args, **kwargs)

    def stop_client(self) -> None:
        super().stop_client()
        self.close_counter += 1


class TestMulticallSocket:
    def setup_method(self):
        self.client_cls = MockSyncClient

    def test_two_calls(self, httpserver: HTTPServer):
        # Prevent "Bad file descriptor" error in parallels calls
        def slow_request(request: Request) -> Response:
            items = [{"id": i, "name": str(i)} for i in range(10)]
            sleep(0.5)
            return Response(json.dumps(items))

        base_url = httpserver.url_for("")
        httpserver.expect_request("/items").respond_with_handler(slow_request)

        client = self.client_cls(base_url, auto_start=True, auto_close=True)

        executor = ThreadPoolExecutor(max_workers=2)
        a = executor.submit(client.sync_list)
        b = executor.submit(client.sync_list)

        while not a.done():
            ...
        a.result()
        while not b.done():
            ...
        b.result()

        assert len(httpserver.log) == 2
        assert client.close_counter == 1
