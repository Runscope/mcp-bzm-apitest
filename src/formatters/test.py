from typing import List, Any, Optional
from src.models.test import Test, TestEnvironments


def format_tests(tests: List[Any], params: Optional[dict] = None) -> List[Test]:
    formatted_tests = []
    for test in tests:
        formatted_tests.append(
            Test(**test).model_dump(by_alias=False)
        )
    return formatted_tests


def format_test_environments(environments: List[Any], params: Optional[dict] = None) -> List[Any]:
    formatted_environments = []
    for environment in environments:
        formatted_environments.append(TestEnvironments(
            **environment).model_dump(by_alias=False))
    return formatted_environments
