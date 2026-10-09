from typing import Any, List, Optional

from src.models.usage import BucketUsage, TeamUsage, TestUsage


def format_team_usage(usages: List[Any], params: Optional[dict] = None) -> List[TeamUsage]:
    formatted = []
    for usage in usages:
        formatted.append(TeamUsage(**usage).model_dump(by_alias=False))
    return formatted


def format_bucket_usage(usages: List[Any], params: Optional[dict] = None) -> List[BucketUsage]:
    """api returns null bucket_key/requests_count/dates when the bucket had no usage in the
    window (it only populates them for buckets present in the usage data). That is a
    legitimate zero, so report it as 0 under the requested bucket_key rather than failing."""
    requested_key = (params or {}).get("bucket_key")
    formatted = []
    for usage in usages:
        usage = dict(usage or {})
        if usage.get("requests_count") is None:
            usage["requests_count"] = 0
        if usage.get("bucket_key") is None:
            usage["bucket_key"] = requested_key
        formatted.append(BucketUsage(**usage).model_dump(by_alias=False))
    return formatted


def format_test_usage(usages: List[Any], params: Optional[dict] = None) -> List[TestUsage]:
    formatted = []
    for usage in usages:
        formatted.append(TestUsage(**usage).model_dump(by_alias=False))
    return formatted
