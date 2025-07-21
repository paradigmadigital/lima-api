# File upload
:::{versionadded} 1.4.0
Support for upload files
:::

In order to upload a file you could do it typing with IO, TextIO or BinaryIO types or with lima_api.FileParameter .


```python
from typing import (
    BinaryIO,
    IO,
    TextIO,
    Union,
)

from httpx._types import FileTypes
import lima_api

class AsyncClient(lima_api.LimaApi):

    @lima_api.post("/upload")
    async def file_upload(self, *, file: Union[IO, TextIO, BinaryIO]) -> None: ...

    @lima_api.post("/upload_pdf")
    async def file_upload_param(self, *, file: FileTypes = lima_api.FileParameter(alias="pdf")) -> None: ...
```
