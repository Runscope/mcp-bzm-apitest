"""
Team models for BlazeMeter API Monitoring
"""
from typing import Optional, Dict, List
from pydantic import BaseModel, Field


class Bucket(BaseModel):
    """Bucket model representing a bucket within a team."""
    key: str = Field(description="The unique identifier key of the bucket present in the team")
    name: str = Field(description="The name of the bucket present in the team")
    default: bool = Field(description="Whether this is the default bucket for this team")


class TeamUsers(BaseModel):
    """Team user model representing a user within a team."""
    user_id: str = Field(
        alias="id", description="The user unique id also known as user_id who is a member of the team")
    name: str = Field(description="The name of the user who is a member of the team")
    email: str = Field(description="The email address of the user who is a member of the team")


class Team(BaseModel):
    """Team model representing a team instance."""
    name: str = Field(description="The name of the team")
    id: str = Field(alias="uuid", description="The unique identifier ID of the team")
    created_at: str = Field(description="Creation timestamp")
    additional_billing_emails: Optional[str] = Field(default=None, description="Additional billing emails")
    buckets: List[Bucket] = Field(description="List of buckets present in the team")
    user_count: int = Field(description="Number of users in the team")
    bucket_count: int = Field(description="Number of buckets present in the team")
    subteams: List[str] = Field(description="List of subteams")
    created_by: TeamUsers = Field(description="User details who created the team")
    owned_by: TeamUsers = Field(description="User details who owns the team currently")
    user_ids: List[str] = Field(alias="user_uuids",
                                description="List of user IDs who are the members of the team")


class AccountTeamObj(BaseModel):
    """Team model representing a team within an account."""
    team_id: str = Field(alias="id", description="The team unique id")
    name: str = Field(description="The name of the team")


class Account(BaseModel):
    """Account model representing a collection of teams user has access to."""
    user_id: str = Field(
        alias="id", description="User unique id also known as user_id")
    name: str = Field(description="The name of the user")
    email: str = Field(description="The email address of the user")
    teams: Optional[List[AccountTeamObj]] = Field(
        description="The list of teams this user has access to")
