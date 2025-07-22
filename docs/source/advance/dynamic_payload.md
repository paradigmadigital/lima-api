# Dynamic payload

In some cases we neet to send payloads with square brackets to the server side,
or the information cannot be specify typing, because of that kwargs_mode param was added.

```{eval-rst}
.. autoclass:: lima_api.constants.KwargsMode
   :members:
   :undoc-members:
   :show-inheritance:
```

You could use `kwargs_mode` pamater for send all kwargs as payload.

```python
import lima_api

class AsyncClient(lima_api.LimaApi):
    @lima_api.get(
        "/datatables",
        kwargs_mode=lima_api.constants.KwargsMode.QUERY,
    )
    async def get_datatables_proxy(self, **kwargs) -> dict: ...

    @lima_api.post(
        "/datatables",
        kwargs_mode=lima_api.constants.KwargsMode.BODY
    )
    async def post_datatables_proxy(self, **kwargs) -> dict: ...
```

## Datatable
This function could be useful for [Datatables Server side](https://datatables.net/manual/server-side) cause allow do not define all fields, but send all of them.
