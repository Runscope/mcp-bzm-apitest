"""
Usage models for BlazeMeter API Monitoring (request-count usage over a window).
"""

from typing import Optional

from pydantic import BaseModel, Field


class TeamUsage(BaseModel):
    """Team-level request-count usage over a window."""

    team_uuid: str = Field(description="The unique identifier of the team the count belongs to")
    requests_count: int = Field(description="Total HTTP requests for the team in the window")
    from_date: str = Field(description="Start of the window the count spans (YYYY-MM-DD)")
    to_date: str = Field(
        description="End of the window (YYYY-MM-DD), exclusive: the day after the last day counted"
    )


class BucketUsage(BaseModel):
    """Bucket-level request-count usage over a window."""

    bucket_key: str = Field(description="The unique identifier of the bucket the count belongs to")
    requests_count: int = Field(description="Total HTTP requests for the bucket in the window")
    from_date: Optional[str] = Field(
        default=None,
        description="Start of the window the count spans (YYYY-MM-DD); absent when the bucket had no usage",
    )
    to_date: Optional[str] = Field(
        default=None,
        description="End of the window (YYYY-MM-DD), exclusive: the day after the last day counted; "
        "absent when the bucket had no usage",
    )


class TestUsage(BaseModel):
    """Test-level request-count usage over a window."""

    test_uuid: str = Field(description="The unique identifier of the test the count belongs to")
    requests_count: int = Field(description="Total HTTP requests for the test in the window")
    from_date: str = Field(description="Start of the window the count spans (YYYY-MM-DD)")
    to_date: str = Field(description="Last day of the window (YYYY-MM-DD), inclusive")
