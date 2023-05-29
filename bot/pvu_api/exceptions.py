class PVUException(BaseException):
    def __init__(self, status: int, msg: str):
        self.status = status
        self.msg = msg

    def __str__(self):
        return f"(status {self.status}) {self.msg}"
