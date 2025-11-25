from typing import Any, List, Optional

from src.models.environment import Environment


def format_environments(environments: List[Any], params: Optional[dict] = None) -> List[Environment]:
    formatted_environments = []
    for environment in environments:
        formatted_environments.append(Environment(**environment).model_dump(by_alias=False))
    return formatted_environments
