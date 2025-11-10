from typing import List, Any, Optional

from src.models.step import TestStep


def format_steps(steps: List[Any], params: Optional[dict] = None) -> TestStep:
	formatted_steps = []
	for step in steps:
		formatted_steps.append(
			TestStep(**step)
		)
	return formatted_steps
