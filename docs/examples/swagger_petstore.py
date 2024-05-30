import asyncio
from enum import Enum
from typing import Optional

from pydantic import BaseModel
from pydantic.fields import Field

import lima_api


class Category(BaseModel):
    identifier: int = Field(alias="id")
    name: str


class Tag(BaseModel):
    identifier: int = Field(alias="id")
    name: str


class PetStatus(str, Enum):
    AVAILABLE = "available"
    PENDING = "pending"
    SOLD = "sold"


class Pet(BaseModel):
    identifier: int = Field(alias="id")
    name: str
    category: Optional[Category]
    photo_urls: Optional[list[str]] = Field(alias="photoUrls")
    tags: list[Tag]
    status: PetStatus


class PetUpdateStatus(BaseModel):
    name: str
    status: str


class PetNotFoundError(lima_api.LimaException): ...


class InvalidDataError(lima_api.LimaException): ...


class PetApi(lima_api.LimaApi):
    response_mapping = {
        404: PetNotFoundError,
    }

    @lima_api.get(
        "/pet/{petId}",
        response_mapping={
            400: InvalidDataError,
        }
    )
    async def get_pet(self, *, petId: int) -> Pet: ...

    @lima_api.get(
        "/pet/{petId}",
        response_mapping={
            400: InvalidDataError,
        }
    )
    async def get_pet_by_id(
        self,
        *,
        pet_id: int = lima_api.PathParameter(alias="petId"),
    ) -> Pet:
        """
        Same call that get_pet(petId=pet_id)
        """
        ...

    @lima_api.post(
        "/pets/{petId}",
        headers={"content-type": "application/x-www-form-urlencoded"},
        response_mapping={405: InvalidDataError}
    )
    async def get_update_pet(self, *, petId: int, data: PetStatus) -> None: ...

    @lima_api.post(
        "/pets/{petId}",
        headers={"content-type": "application/x-www-form-urlencoded"},
        response_mapping={405: InvalidDataError}
    )
    async def get_update_pet_by_id(
        self,
        *,
        pet_id: int = lima_api.PathParameter(alias="petId"),
        data: PetStatus = lima_api.BodyParameter(),
    ) -> None:
        """
        Same call that get_update_pet(petId=pet_id, data=data)
        """
        ...

    @lima_api.get("/pet/findByStatus")
    async def filter(
        self,
        *,
        status: list[PetStatus] = lima_api.QueryParameter(default=[]),
    ) -> list[Pet]: ...


if __name__ == "__main__":
    async def main():
        pet_client = PetApi("https://petstore.swagger.io/v2")
        async with pet_client:
            for status in [PetStatus.PENDING, PetStatus.SOLD, PetStatus.AVAILABLE]:
                pets = await pet_client.filter(status=[status])
                for pet in pets:
                    read_pet = await pet_client.get_pet(petId=pet.identifier)
                    print(read_pet)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
