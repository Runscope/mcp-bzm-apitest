from typing import Any, List, Optional

from src.models.team import Account, Team, TeamUsers


def format_teams(teams: List[Any], params: Optional[dict] = None) -> List[Team]:
    formatted_teams = []
    for team in teams:
        formatted_teams.append(Team(**team).model_dump(by_alias=False))
    return formatted_teams


def format_accounts(accounts: List[Any], params: Optional[dict] = None) -> List[Account]:
    formatted_accounts = []
    for account in accounts:
        formatted_accounts.append(Account(**account).model_dump(by_alias=False))
    return formatted_accounts


def format_team_users(users: List[Any], params: Optional[dict] = None) -> List[TeamUsers]:
    formatted_users = []
    for user in users:
        formatted_users.append(TeamUsers(**user).model_dump(by_alias=False))
    return formatted_users
