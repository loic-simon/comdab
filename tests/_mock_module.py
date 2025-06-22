from functools import lru_cache
from unittest.mock import Mock


@lru_cache()
def __getattr__(item: object) -> Mock:
    return Mock()
