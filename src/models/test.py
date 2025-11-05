"""
Test models for BlazeMeter API Monitoring
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class CreatedBy(BaseModel):
    """User who created the test."""
    id: str = Field(
        description="User who created this test. Also known as user_id")
    email: str = Field(
        description="Email address of the user who created this test")
    name: str = Field(description="Name of the user who created this test")


class LastTestRun(BaseModel):
    """Last test run result. Only keeping test_run_id and status for brevity.
       Client(AI) can use the test_run_id to fetch the full test result details if needed.
    """
    id: str = Field(
        description="The unique identifier for the test run. Also known as test_run_id")
    status: str = Field(
        description="The status of the test run. Possible values: 'completed', 'error', 'expired', "
                    "'canceled'")


class TestStepMini(BaseModel):
    """ Test Step object. Only keeping test step id and step type for brevity.
        Client(AI) can use the step id to fetch the full test step details if needed.
    """
    id: str = Field(
        description="The unique identifier for the test step. Also known as step_id")
    step_type: str = Field(
        description="The type of the test step. Possible values: 'request', 'pause', 'conditional', "
                    "'conditional-loop', 'subtest' and 'inbound'")


class Test(BaseModel):
    """API Test basic model with essential fields only.

    This model intentionally excludes fields like environments, schedules,
    and detailed step configurations which can be fetched via separate APIs:
    - GET /buckets/{bucket_key}/tests/{test_id}/environments
    - GET /buckets/{bucket_key}/tests/{test_id}/schedules
    - GET /buckets/{bucket_key}/tests/{test_id}/steps/{step_id}
    """
    id: str = Field(
        description="The unique identifier for the test. Also known as test_id")
    name: str = Field(description="The name of the test")
    description: Optional[str] = Field(
        default=None, description="The description of the test")
    default_environment_id: str = Field(
        description="The default environment ID")
    trigger_url: str = Field(
        description="The trigger URL. It is used to start test runs via API")
    created_by: CreatedBy
    created_at: float = Field(
        description="The timestamp when the test was created (Unix timestamp)")
    steps: List[TestStepMini] = Field(
        default_factory=list, description="Steps present in the test")
    step_count: int = Field(
        default=0, description="Total steps count in the test")
    last_run_created_at: Optional[float] = Field(
        default=None, description="The timestamp when the test was last run (Unix timestamp)")
    last_run: Optional[LastTestRun] = Field(
        default=None, description="Last test run result")


class CreateTest(BaseModel):
    """Model for creating a new API Test."""
    name: str = Field(description="The name of the test to be created")
    description: Optional[str] = Field(
        default=None, description="The description of the test to be created")


class UpdateTest(BaseModel):
    pass