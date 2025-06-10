# Parameters 
:::{note}
* The Body param must be allways BaseModel class and only one is valid
* Functions wrapped by lima_api always must use *, in order to force use keywords for calling functions.
* All parameters must be typed.
:::

The functions parameters will mapping with the following criteria.

## Payload location
The parameters that extend from `pydantic.BaseModel` will send to body by default 
except if the method is `GET`, in this case will send as query params.
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

## Path parameters
At the end with the regex expressed in [`LimaSettings.lima_bracket_regex`](#lima_api.config.LimaSettings.lima_bracket_regex)
will get the names in the path params and macht the param names defined in the function.

For example with `lima_bracket_regex = r"\[(.+?)\]"`
```python
@lima_api.get("/pets/[petId]")
async def get_pet(self, *, petId: str) -> Pet: ...
```

## Defined location
You could define the location of the param using `lima_api.LimaParameter`
(one of the followings, `lima_api.FileParameter`, `lima_api.PathParameter`, `lima_api.QueryParameter` or `lima_api.BodyParameter`) classes.
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

## File parameter
:::{versionadded} 1.4.0
Support for upload files
:::

See more details in [upload_files](usecases/upload_files.md)

# Parameter dump mode
In Query parameters you could use different kind of dumps for Pydantic classes.

By default, model will be converted as a dict `lima_api.parameters.DumpMode.DICT`.
You could use the following options based on you preference.
* *lima_api.parameters.DumpMode.DICT_NONE*: Will including `None` values.
* *lima_api.parameters.DumpMode.JSON*: The param will send as json without None values.
* *lima_api.parameters.DumpMode.JSON_NONE*: The param will send as json including None values.

## Example:
With the following code:
```python
class ExampleQuery(BaseModel):
    page: Optional[int] = None
    size: Optional[int] = None

class ExampleQueryModelDumpClient(lima_api.SyncLimaApi):
    @lima_api.get("/")
    def example(self, *, query: ExampleQuery = lima_api.QueryParameter()) -> None: ...

client = ExampleQueryModelDumpClient(base_url="http://localhost")
client.example(query=ExampleQuery(page=0))
```
The result will be the following based on the value of `model_dump_mode`

* **lima_api.parameters.DumpMode.DICT:** `page=0`
* **lima_api.parameters.DumpMode.DICT_NONE:** `page=0&size=`
* **lima_api.parameters.DumpMode.JSON:** `query=%7B"page"%3A0%7D`
* **lima_api.parameters.DumpMode.JSON_NONE:** `query=%7B"page"%3A0%2C"size"%3Anull%7D`
