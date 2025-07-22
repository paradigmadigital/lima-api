# Recommendations

## Create a iterator for pageable response
In some case you want remove APIs complexity (for example, 
pagination) for that cases you could create a private function
with the lima decorator and public one without it:
``` python
class StApi(lima_api.LimaApi):
    @lima_api.get("/v1/rest/animal/search")
    async def _animals_search(
        self,
        *,
        page_number: int = lima_api.QueryParameter(alias="pageNumber"),
        page_size: int = lima_api.QueryParameter(alias="pageSize", default=100),
    ) -> AnimalBaseResponse: ...

    async def list_animals(self) -> AsyncIterator[AnimalBase]:
        page_number = 0
        page = await self._animals_search(page_number=page_number)
        while not page.page.lastPage:
            for animal in page.animals:
                yield animal
            page_number += 1
            page = await self._animals_search(page_number=page_number)
        for animal in page.animals:
            yield animal
```

## auto_start and auto_stop

The recommended way to use a Client is as a context manager.
This will ensure that connections are properly cleaned up when leaving.
```python
with YourClient(base_url="http://localhost") as client:
    ...
```

You can explicitly close the connection pool without block-usage using `stop_client`:
```python
client = YourClient(base_url="http://localhost")
try:
    client.start_client()
    ...
finally:
    client.stop_client()
```

The last option is create the client instance with `auto_start`, that will start client automatic and close on each request.
In sync clients you could use the `auto_close` to close on each request or not.
```python
client = YourClient(base_url="http://localhost", auto_start=True)
...
```

:::{important}
* If you open and close the connection many times the performance could be affected.
* With `auto_start` mode raise conditions could be happened.
* `auto_close` is only supported in sync clients, and only could set if auto_start is True.
:::

:::{note}
If in your case of use you will have a common and continue connection to some server 
maybe use auto_start without auto_close could be useful.
:::
