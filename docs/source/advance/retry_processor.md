# Retry processor
:::{versionadded} 1.4.0
Support for retry when exceptions are raised
:::

All retry processors must be instanced of `lima_api.core.LimaRetryProcessor`.

That processors allow is adding automatic actions for your failed request,
in order to you could fix the issue and retry.  

## Use it
You could use at top level client or in a function by `retry_mapping`:
```python
class AsyncClient(lima_api.LimaApi):
    retry_mapping = {UNAUTHORIZED: lima_api.retry_processors.AutoLoginProcessor}

    @lima_api.get(
        "/healthcheck",
        retry_mapping={TOO_MANY_REQUESTS: lima_api.retry_processors.RetryAfterProcessor},
    )
    async def healthcheck(self) -> None: ...
```

You could extend from `lima_api.core.LimaRetryProcessor` to create you own retry processors.  
```{autodoc2-object} lima_api.core.LimaRetryProcessor
render_plugin = "myst"
no_index = true
```

## How it works

When a request is created if some exception is raised,
the system will check the status code and the dict of `retry_mapping`.
1. If exists the status a new class is created or reused (this instance is per request not for all client).
2. Function `do_retry` is called and if returns `False` the exception will be raised in other case `process` will be called.
3. If `process` returns `False` the exception will be raised in other case the request will be retried.

:::{note}
In sync clients you must make the `process` flow on `do_retry` because `process` will not be called in a sync clients.
:::

## Builds processors

### RetryAfterProcessor
Located at `lima_api.retry_processors.RetryAfterProcessor`.

```{autodoc2-docstring} lima_api.retry_processors.RetryAfterProcessor
render_plugin = "myst"
```

### AutoLoginProcessor
Located at `lima_api.retry_processors.AutoLoginProcessor`.

```{autodoc2-docstring} lima_api.retry_processors.AutoLoginProcessor
render_plugin = "myst"
```