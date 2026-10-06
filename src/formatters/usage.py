from typing import Any, List, Optional

from src.models.usage import BucketUsage, TeamUsage, TestUsage


def format_team_usage(usages: List[Any], params: Optional[dict] = None) -> List[TeamUsage]:
    formatted = []
    for usage in usages:
        formatted.append(TeamUsage(**usage).model_dump(by_alias=False))
    return formatted


def format_bucket_usage(usages: List[Any], params: Optional[dict] = None) -> List[BucketUsage]:
    formatted = []
    for usage in usages:
        formatted.append(BucketUsage(**usage).model_dump(by_alias=False))
    return formatted


def format_test_usage(usages: List[Any], params: Optional[dict] = None) -> List[TestUsage]:
    formatted = []
    for usage in usages:
        formatted.append(TestUsage(**usage).model_dump(by_alias=False))
    return formatted
