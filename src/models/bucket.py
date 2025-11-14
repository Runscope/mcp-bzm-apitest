"""
Bucket models for BlazeMeter API Monitoring
"""
from typing import Optional, Dict
from pydantic import BaseModel, Field


class Team(BaseModel):
    """Team model representing a team."""
    team_id: str = Field(alias="id", description="The team unique id")
    name: str = Field(description="The name of the team")


class Bucket(BaseModel):
    """Bucket model representing a collection of tests."""
    bucket_key: str = Field(alias="key", description="The bucket unique id")
    name: str = Field(description="The name of the bucket")
    created_at: float | int = Field(
        description="The timestamp when the bucket was created (Unix timestamp)")
    default: bool = Field(
        description="Whether the bucket is the default bucket for the team")
    is_private: bool = Field(
        description="Whether the bucket is private or public")
    tests_count: Optional[int] = Field(
        default=None, description="Number of tests in the bucket")
    trigger_url: str = Field(
        description="The URL to start the bucket-level test runs via API")
    team: Optional[Team] = Field(description="The team this bucket belongs to")
