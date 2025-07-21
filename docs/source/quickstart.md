# Quick Start

## Create your models.
Use the [Pydantic](https://docs.pydantic.dev/latest/) models to create your custom models.
```python
from pydantic import BaseModel
from pydantic.fields import Field

class Pet(BaseModel):
    identifier: int = Field(alias="id")
    name: str
```
   
## Create your exceptions.
Extend from `lima_api.LimaException` to create your custom error classes.
```python
import lima_api

class PetNotFoundError(lima_api.LimaException):
    detail = "Pet not found"

class InvalidDataMessage(BaseModel):
    message: str
    code: str

class InvalidDataError(lima_api.LimaException):
    model = InvalidDataMessage
```
   
## Create your client.
Extend from `lima_api.SyncLimaApi` or `lima_api.LimaApi` to create you sync or async client.
```python
import lima_api
...

class PetApi(lima_api.LimaApi):
    response_mapping = {
        404: PetNotFoundError,
    }
```
   
:::{caution}
* Synchronous clients only support synchronous functions, and in the same way with asynchronous.
* You could see other code examples at [docs/examples](../examples/) folder.
:::

### Create functions.
In order to call to some entrypoint you should create your function with the proper decorator.
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

:::{attention}
* The Body param must be **allways** `BaseModel` class and only one is valid
* Functions wrapped by lima_api always must use _*_ ([Keyword-Only](https://peps.python.org/pep-3102/)),
in order to force use keywords for calling functions.
* All parameters must be typed.
:::

## Instance your client.
For make connection to the remote server you need to start the connection.
You could do that ussing `with` statement as below:
```python
pet_client = PetApi("https://petstore.swagger.io/v2")
async with pet_client:
    pet = await pet_client.get_pet(pet_id=1)
```
