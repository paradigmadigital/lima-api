class LimaException(Exception):
    def __init__(self, detail: str = "Error de Lima", status_code: int = 0, content: bytes = b""):
        self.detail = detail
        self.status_code = status_code
        self.content = content

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        return f"{class_name}(detail={self.detail!r}, status_code={self.status_code!r})"
