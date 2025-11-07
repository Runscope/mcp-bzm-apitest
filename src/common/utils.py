from datetime import datetime
from typing import Optional, Callable


def get_date_time_iso(timestamp: int) -> Optional[str]:
    if timestamp is None:
        return None
    else:
        return datetime.fromtimestamp(timestamp).isoformat()
