"""
Team models for BlazeMeter API Monitoring
"""
from typing import Optional, Dict, List
from pydantic import BaseModel, Field

class Team(BaseModel):
	"""Team model representing a collection of teams."""
	pass

class TeamUsers(BaseModel):
	"""Team user model representing a user within a team."""
	user_id: str = Field(alias="id", description="The user unique id also known as user_id")
	name: str = Field(description="The name of the user")
	email: str = Field(description="The email address of the user")


class AccountTeamObj(BaseModel):
    """Team model representing a team within an account."""
    team_id: str = Field(alias="id", description="The team unique id")
    name: str = Field(description="The name of the team")
    # owner: bool = Field(description="Whether the team owns the team")


class Account(BaseModel):
	"""Account model representing a collection of teams user has access to."""
	user_id: str = Field(alias="id", description="User unique id also known as user_id")
	name: str = Field(description="The name of the user")
	email: str = Field(description="The email address of the user")
	teams: Optional[List[AccountTeamObj]] = Field(description="The teams this user has access to")
