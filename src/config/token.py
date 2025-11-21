import os
from pathlib import Path
from typing import Union
from functools import lru_cache
from dotenv import load_dotenv


class BzmApimTokenError(Exception):
    """Error when constructing or loading BzmApimToken."""
    pass


class BzmApimToken:
    __slots__ = ("token")

    def __init__(self, token: str):
        if not token or not isinstance(token, str):
            raise BzmApimTokenError(f"Invalid Token : {token!r}")

        self.token = token

    @classmethod
    @lru_cache(maxsize=1)
    def from_file(cls, path: Union[str, Path]) -> "BzmApimToken":
        p = Path(path)
        if not p.exists() or not p.is_file():
            raise BzmApimTokenError(f"File does not exist: {p!r}")

        try:
            load_dotenv(dotenv_path=p)
            token_val = os.getenv("BZM_API_TEST_TOKEN")
        except Exception as e:
            raise BzmApimTokenError(
                f"Error reading/parsing Token from {p!r}: {e}") from e

        return cls(token=token_val)

    def __repr__(self):
        return f"<BzmApimToken={self.token!r}>"
