from typing import List, Any, Optional
from src.models.schedule import Schedule


def format_schedules(schedules: List[Any], params: Optional[dict] = None) -> List[Schedule]:
    formatted_schedules = []
    for schedule in schedules:
        formatted_schedules.append(
            Schedule(**schedule).model_dump(by_alias=False)
        )
    return formatted_schedules
