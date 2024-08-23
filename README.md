# Lima-API
Lima-API is sync and async library that allows implements Rest APIs libs with python typing.

You could read more about it on [our post (Spanish)](https://www.paradigmadigital.com/dev/poder-del-tipado-python-funciones-sin-codigo/).

You could install from [pypi](https://pypi.org/project/lima-api/) with:
```shell
pip install lima-api
```

# Howto use it
1. Create your [Pydantic](https://docs.pydantic.dev/latest/) models.
    ```python
    from pydantic import BaseModel
    from pydantic.fields import Field

    class Pet(BaseModel):
        identifier: int = Field(alias="id")
        name: str
    ```
2. Create your exceptions extend from `lima_api.LimaException`
    ```python
    import lima_api

    class PetNotFoundError(lima_api.LimaException): ...

    class InvalidDataError(lima_api.LimaException): ...
    ```
3. Create your class extend from `lima_api.SyncLimaApi` or `lima_api.LimaApi`.
    ```python
    import lima_api
    ...

    class PetApi(lima_api.LimaApi):
        response_mapping = {
            404: PetNotFoundError,
        }
    ```
4. Create functions with the proper decorator.
    ```python
    import lima_api
    ...

    class PetApi(lima_api.LimaApi):
        ...

        @lima_api.get(
            "/pet/{petId}",
            response_mapping={
                400: InvalidDataError,
            }
        )
        async def get_pet(self, *, petId: int) -> Pet:
            ...
    ```
5. Create the client instance.
    ```python
    pet_client = PetApi("https://petstore.swagger.io/v2")
    async with pet_client:
        pet = await pet_client.get_pet(pet_id=1)
    ```


In some case you want remove APIs complexity( for example, pagination creating a private function with decorator and public one without it:
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
        page = await self._search(page_number=page_number)
        while not page.page.lastPage:
            for animal in page.animals:
                yield animal
            page_number += 1
            page = await self._search(page_number=page_number)
        for animal in page.animals:
            yield animal
```

> [!NOTE]
> * Synchronous clients only support synchronous functions, and in the same way with asynchronous.
> * You could see other code examples at [docs/examples](docs/examples) folder.


> [!IMPORTANT]
> * The Body param must be allways `BaseModel` calls and only one is valid
> * Functions wrapped by lima_api always must use *, in order to force use keywords for calling functions.


# Parameters types
The functions parameters will mapping with the following criteria.
1. You could define the location of the param using `lima_api.LimaParameter` (one of the followings `lima_api.PathParameter`, `lima_api.QueryParameter` or `lima_api.BodyParameter`) classes.
   ```python
    from enum import Enum

    import lima_api
    from pydantic import BaseModel
    ...

    class PetUpdateStatus(BaseModel):
        name: str
        status: str
   
    class PetStatus(str, Enum):
        AVAILABLE = "available"
        PENDING = "pending"
        SOLD = "sold"

    class PetApi(lima_api.LimaApi):
        ...

        @lima_api.post(
            "/pets/{petId}",
            headers={"content-type": "application/x-www-form-urlencoded"},
            response_mapping={405: InvalidDataError}
        )
        async def get_update_pet(
            self,
            *,
            pet_id: int = lima_api.PathParameter(alias="petId"),
            data: PetUpdateStatus = lima_api.BodyParameter(),
        ) -> None: ...
    
        @lima_api.get("/pet/findByStatus")
        async def filter(
            self,
            *,
            status: list[PetStatus] = lima_api.QueryParameter(default=[]),
        ) -> list[Pet]: ...
   ```
2. The parameters that extend from `pydantic.BaseModel` will send to body by default except if the method is `GET`, in this case will send as query params.
   ```python
    from enum import Enum

    import lima_api
    from pydantic import BaseModel
    ...

    class PetStatus(str, Enum):
        AVAILABLE = "available"
        PENDING = "pending"
        SOLD = "sold"

    class PetFilterStatus(BaseModel):
        status: list[PetStatus]


    class PetApi(lima_api.LimaApi):
        ...

        @lima_api.get("/pet/findByStatus")
        async def filter(self, *, status: list[PetStatus]) -> list[Pet]: ...

        @lima_api.get("/pet/findByStatus")
        async def filter_by_obj(self, *, data: PetFilterStatus) -> list[Pet]: ...
   ```
3. At the end with the regex expressed in `LimaSettings.lima_bracket_regex` will get the names in the path params and macht the param names defined in the function.

   For example with `lima_bracket_regex = r"\[(.+?)\]"`
   ```python
    @lima_api.get("/pets/[petId]")
    async def get_pet(self, *, petId: str) -> Pet: ...
   ```


## Auto-start

In some case we need create a global client. In that cases maybe you don't want use `with` cause when you call some function. We create the kwarg `auto_start` that allow start and close client automatic when you call some function.

> [!IMPORTANT]
> * If you open and close the connection the performance could be affected.

> [!NOTE]
> * Synchronous clients allows use `auto_close` (as False by default to have same behavior that Asynchronous has) that allow not close the connection to improve the performance.
> * We recommend use `with` in Asynchronous and in Synchronous mode with `auto_start=True` and `auto_close=False`.


## Helps for developers

By default, lima-api don't log any information, whoever in some cases you need log information.

In order to solve this and becases the log level could be different for each case, we decide create the function `def log(self, *, event: lima_api.LogEvent, **kwargs)` which could be overwritten.

```python
class PetApi(lima_api.LimaApi):
    def log(self, *, event: lima_api.LogEvent, **kwargs) -> None:
        if event == lima_api.LogEvent.RECEIVED_RESPONSE:
            response: httpx.Response = kwargs.get("response")
            logger.info(
                "Request completed",
                extra={
                    "url": response.request.url,
                    "elapsed": response.elapsed,
                    "method": response.request.method,
                    "service_status": response.status_code,
                }
           )
    ...
```

### Create requirement file locally
```shell
uv pip compile pyproject.toml --extra=test --extra=pydantic2 > requirements.txt
uv pip install requirements.txt
```
