"""
Test Step models for BlazeMeter API Monitoring
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class TestStep(BaseModel):
    """Individual test step (request)."""
    step_id: str = Field(alias="id", description="Unique test step identifier")
    step_type: str = Field(description="Test step type. Possible values: 'request', 'pause', 'conditional', 'conditional-loop', 'subtest' and 'inbound'")
    skipped: bool = Field(description="Whether test step is skipped for execution or not")
    duration: Optional[int] = Field(default=None,
                                    description="Pause duration in seconds. Only valid for Pause step_type")
    note: Optional[str] = Field(default=None, description="Test step note or a small description")
    auth: Optional[Dict[str, Any]] = Field(default=None, description="Test step authorization information")
    body: Optional[str] = Field(default=None,
                                description="Test step body either JSON or RAW body as strings")
    form: Optional[Dict[str, Any]] = Field(default=None,
                                           description="Test request step form body to send x-www-form-urlencoded data")
    multipart_form: Optional[List[Any]] = Field(default=None,
                                                description="Test request step multipart form body to send files")
    binary_body: Optional[List[Any]] = Field(default=None, description="Test request step binary body")
    headers: Optional[Dict[str, Any]] = Field(default=None, description="Test request step headers")
    method: Optional[str] = Field(default=None, description="Test step request HTTP method")
    url: Optional[str] = Field(default=None, description="The full URL for the API request")
    assertions: Optional[List[Dict[str, Any]]] = Field(default=None,
                                                       description="Assertions defined for this test step")
    variables: Optional[List[Dict[str, Any]]] = Field(default=None,
                                                      description="Extraction variables defined for this test step.")
    scripts: Optional[List[str]] = Field(default=None,
                                         description="Post api response javascript scripts. This can be used to extract variables from response or do some custom validations.")
    before_scripts: Optional[List[str]] = Field(default=None,
                                                description="Pre api request javascript scripts. This can be used to set variables or do some pre-processing before the request is sent.")
    steps: Optional[List[Dict[str, Any]]] = Field(default=None,
                                                  description="Sub-steps for conditional if and loop step types.")
    comparison: Optional[str] = Field(default=None,
                                      description="Comparison between left and right value for conditional if and loop step types")
    left_value: Optional[str] = Field(default=None,
                                      description="Left value for comparison in conditional if and loop step types")
    right_value: Optional[str] = Field(default=None,
                                       description="Right value for comparison in conditional if and loop step types")
    test_uuid: Optional[str] = Field(default=None,
                                     description="test_id of the subtest to be executed. Only valid for subtest step type")
    bucket_key: Optional[str] = Field(default=None,
                                      description="bucket_key of the subtest to be executed. Only valid for subtest step type")