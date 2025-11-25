from typing import Any, List, Optional

from src.models.bucket import Bucket


def format_buckets(buckets: List[Any], params: Optional[dict] = None) -> List[Bucket]:
    formatted_buckets = []
    for bucket in buckets:
        formatted_buckets.append(Bucket(**bucket).model_dump(by_alias=False))
    return formatted_buckets
