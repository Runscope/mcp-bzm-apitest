"""
Test Step models for BlazeMeter API Monitoring
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class TestStep(BaseModel):
    """Individual test step (request)."""
    id: str
    step_type: str = "request"  # "request", "pause", "condition"
    skipped: bool = False
    note: str = ""
    auth: Dict[str, Any] = {}
    body: Optional[str] = None
    form: Optional[Dict[str, Any]] = None
    multipart_form: List[Any] = []
    binary_body: List[Any] = []
    headers: Dict[str, str] = {}
    method: str  # GET, POST, PUT, DELETE, etc.
    url: str
    assertions: List[Assertion] = []
    variables: List[Variable] = []
    scripts: List[str] = []  # Post-response scripts
    before_scripts: List[str] = []  # Pre-request scripts