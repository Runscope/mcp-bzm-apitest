from typing import List, Any, Optional
from src.models.result import TestExecution, TestResult, BucketLevelTestResult


def format_triggered_runs(runs: List[Any], params: Optional[dict] = None) -> List[TestExecution]:
    formatted_runs = []
    for run in runs:
        formatted_runs.append(
            TestExecution(**run).model_dump(by_alias=False)
        )
    return formatted_runs


def format_results(results: List[Any], params: Optional[dict] = None) -> List[TestResult]:
    formatted_results = []
    for result in results:
        formatted_results.append(
            TestResult(**result).model_dump(by_alias=False)
        )
    return formatted_results


def format_bucket_level_results(
        results: List[Any], params: Optional[dict] = None) -> List[BucketLevelTestResult]:
    formatted_results = []
    for result in results:
        formatted_results.append(
            BucketLevelTestResult(**result).model_dump(by_alias=False)
        )
    return formatted_results
