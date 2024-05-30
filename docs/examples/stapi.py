import asyncio
import json
from enum import Enum
from typing import Optional, AsyncIterator

from pydantic import BaseModel

import lima_api


class Direction(str, Enum):
    ASC = "ASC"
    DESC = "DESC"


class ResponsePage(BaseModel):
    pageNumber: Optional[int]
    pageSize: Optional[int]
    numberOfElements: Optional[int]
    totalElements: Optional[int]
    totalPages: Optional[int]
    firstPage: Optional[bool]
    lastPage: Optional[bool]


class ResponseSortClause(BaseModel):
    name: str
    direction: Direction
    clauseOrder: int


class ResponseSort(BaseModel):
    clauses: list[ResponseSortClause]


class AnimalBase(BaseModel):
    uid: str
    name: str
    earthAnimal: Optional[bool]
    earthInsect: Optional[bool]
    avian: Optional[bool]
    canine: Optional[bool]
    feline: Optional[bool]


class BaseResponse(BaseModel):
    page: ResponsePage
    sort: ResponseSort


class AnimalBaseResponse(BaseResponse):
    animals: list[AnimalBase]


class UnexpectedError(lima_api.LimaException):
    code: Optional[str] = None
    message: Optional[str] = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            payload = json.loads(self.content)
            self.code = payload.get("code", None)
            self.message = payload.get("message", None)
        except json.JSONDecodeError:
            ...


class StApi(lima_api.LimaApi):
    default_exception = UnexpectedError

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


if __name__ == "__main__":
    async def main():
        stapi = StApi("https://stapi.co/api")
        async with stapi:
            async for animal in stapi.list():
                print(animal)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
