"""
Test Result model for BlazeMeter API Monitoring
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class RequestResult(BaseModel):
    """individual request result within a test run."""
    url: Optional[str] = Field(default=None, description="Request URL")
    method: Optional[str] = Field(default=None, description="HTTP method")
    uuid: str = Field(
        description="Unique identifier for the test step. Also known as step_id")
    result: Optional[str] = Field(
        default=None, description="Result of the request")
    variables: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Variables extracted in this request")
    assertions: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Assertions for this request")
    scripts: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Scripts executed in this request")
    error_messages: Optional[Any] = Field(
        default=None, description="Error messages for this request")
    response_message: Optional[str] = Field(
        default=None, description="Response message")
    assertions_defined: Optional[int] = Field(
        default=None, description="Number of assertions defined")
    assertions_passed: Optional[int] = Field(
        default=None, description="Number of assertions passed")
    assertions_failed: Optional[int] = Field(
        default=None, description="Number of assertions failed")
    variables_defined: Optional[int] = Field(
        default=None, description="Number of variables defined")
    variables_passed: Optional[int] = Field(
        default=None, description="Number of variables passed")
    variables_failed: Optional[int] = Field(
        default=None, description="Number of variables failed")
    scripts_defined: Optional[int] = Field(
        default=None, description="Number of scripts defined")
    scripts_passed: Optional[int] = Field(
        default=None, description="Number of scripts passed")
    scripts_failed: Optional[int] = Field(
        default=None, description="Number of scripts failed")
    timings: Optional[Dict[str, Any]] = Field(
        default=None, description="Timing information for the request")


class TestResult(BaseModel):
    """test run result."""
    test_run_id: str = Field(
        description="The unique identifier for the test run")
    bucket_key: str = Field(
        description="The bucket to which this test run belongs to")
    test_id: str = Field(description="The test this result belongs to")
    test_name: str = Field(description="The name of the test")

    assertions_defined: int = Field(
        description="Number of assertions defined in the test")
    assertions_failed: int = Field(
        description="Number of assertions that failed during the test run")
    assertions_passed: int = Field(
        description="Number of assertions passed during the test run")
    variables_defined: int = Field(
        description="Number of variables extractions defined in the test")
    variables_passed: int = Field(
        description="Number of variables that were extracted successfully during the test run")
    variables_failed: int = Field(
        description="Number of variables that failed to be extracted during the test run")
    scripts_defined: int = Field(
        description="Number of scripts defined in the test")
    scripts_passed: int = Field(
        description="Number of scripts passed during the test run")
    scripts_failed: int = Field(
        description="Number of scripts failed during the test run")

    started_at: float = Field(
        description="The timestamp when the test run started (Unix timestamp)")
    finished_at: float = Field(
        description="The timestamp when the test run finished (Unix timestamp)")
    requests_executed: int = Field(
        description="Number of API requests executed during the test run")
    result: str = Field(
        description="The result of the test run. Possible values: 'pass', 'fail', 'expired'")
    source: str = Field(
        description="The source of the test run. Possible values: 'manual', 'scheduled', 'trigger_url'")
    region: Optional[str] = Field(
        default=None, description="The region where the test run was executed")
    run_by: Optional[str] = Field(
        default=None, description="The name of the user who initiated the test run")
    environment_id: str = Field(
        description="The environment ID used for this test run")
    requests: List[RequestResult] = Field(
        description="List of individual request results within this test run")
