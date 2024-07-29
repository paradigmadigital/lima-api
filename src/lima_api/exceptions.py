from typing import Optional


class LimaException(Exception):
    detail: str = "Error de Lima"
    status_code: int = -1
    content: bytes = b""

    def __init__(
        self,
        *,
        detail: Optional[str] = None,
        status_code: Optional[int] = None,
        content: Optional[bytes] = None,
    ):
        if detail is not None:
            self.detail = detail
        if status_code is not None:
            self.status_code = status_code
        if content is not None:
            self.content = content

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        return f"{class_name}(detail={self.detail!r}, status_code={self.status_code!r})"

    def __str__(self) -> str:
        return self.detail
