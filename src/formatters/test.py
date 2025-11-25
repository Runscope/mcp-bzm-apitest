from typing import Any, List, Optional

from src.models.test import Test, TestMetrics


def format_tests(tests: List[Any], params: Optional[dict] = None) -> List[Test]:
    formatted_tests = []
    for test in tests:
        formatted_tests.append(Test(**test).model_dump(by_alias=False))
    return formatted_tests


def format_test_metrics(metrics: List[Any], params: Optional[dict] = None) -> List[TestMetrics]:
    formatted_metrics = []
    for metric in metrics:
        formatted_metrics.append(TestMetrics(**metric).model_dump(by_alias=False))
    return formatted_metrics
