from typing import List, Any, Optional
from src.models.test import Test


def format_tests(tests: List[Any], params: Optional[dict] = None) -> List[Test]:
    formatted_tests = []
    for test in tests:
        formatted_tests.append(
            Test(**test).model_dump(by_alias=False)
        )
    return formatted_tests
