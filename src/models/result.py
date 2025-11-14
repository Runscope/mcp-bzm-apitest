"""
Test Result model for BlazeMeter API Monitoring
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ScriptResult(BaseModel):
    """Script execution result."""
    output: Optional[str] = Field(default=None, description="Script output")
    error: Optional[str] = Field(
        default=None, description="Script error message")
    result: str = Field(description="Script execution result")


class AssertionResult(BaseModel):
    """Assertion execution result."""
    result: str = Field(description="Assertion result")
    source: str = Field(description="Assertion source")
    property: Optional[str] = Field(
        default=None, description="Property being asserted")
    comparison: str = Field(description="Comparison type")
    target_value: Any = Field(description="Expected value")
    actual_value: Any = Field(description="Actual value")
    error: Optional[str] = Field(default=None, description="Assertion error")


class SubtestRequestResult(BaseModel):
    """Request result within a subtest."""
    response_size_bytes: Optional[int] = Field(
        default=None, description="Response size in bytes")
    url: Optional[str] = Field(default=None, description="Request URL")
    variables: Optional[Dict[str, int]] = Field(
        default=None, description="Variables statistics")
    step_type: Optional[str] = Field(default=None, description="Step type")
    note: Optional[str] = Field(default=None, description="Request note")
    result: str = Field(description="Request result")
    response_status_code: Optional[str] = Field(
        default=None, description="HTTP response status code")
    scripts: Optional[Dict[str, int]] = Field(
        default=None, description="Scripts statistics")
    method: Optional[str] = Field(default=None, description="HTTP method")
    response_time_ms: Optional[int] = Field(
        default=None, description="Response time in milliseconds")
    assertions: Optional[Dict[str, Any]] = Field(
        default=None, description="Assertions statistics and details")


class SubtestDetail(BaseModel):
    """Subtest execution details."""
    name: str = Field(description="Subtest name")
    note: Optional[str] = Field(
        default=None, description="Subtest description")
    result: str = Field(description="Subtest result")
    test_id: str = Field(
        alias="test_uuid",
        description="Id of the parent test which is actually executed by the subtest step")
    test_run_id: str = Field(alias="test_run_uuid",
                             description="Id of the subtest run")
    test_run_url: str = Field(description="Subtest run URL")
    started_at: str = Field(description="Subtest start timestamp")
    finished_at: str = Field(description="Subtest finish timestamp")
    requests: List[SubtestRequestResult] = Field(
        description="Subtest request results")


class RequestResult(BaseModel):
    """Individual request result within a test run."""
    url: Optional[str] = Field(default=None, description="Request URL")
    method: Optional[str] = Field(default=None, description="HTTP method")
    uuid: Optional[str] = Field(
        default=None, description="Unique identifier for the test step")
    result: Optional[str] = Field(
        default=None, description="Result of the request")
    variables: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Variables extracted in this request")
    assertions: Optional[List[AssertionResult]] = Field(
        default=None, description="Assertions for this request")
    scripts: Optional[List[ScriptResult]] = Field(
        default=None, description="Scripts executed in this request")
    error_messages: Optional[List[Any]] = Field(
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
    """Test run result."""
    test_run_id: str = Field(
        description="The unique identifier for the test run")
    bucket_key: str = Field(
        description="The bucket to which this test run belongs to")
    test_id: str = Field(description="The test this result belongs to")
    test_name: Optional[str] = Field(
        default=None, description="The name of the test")

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
    finished_at: Optional[float] = Field(
        default=None, description="The timestamp when the test run finished (Unix timestamp)")
    requests_executed: int = Field(
        description="Number of API requests executed during the test run")
    result: str = Field(description="The result of the test run")
    source: str = Field(
        description="The source of the test run. Possible values are - 'manual', 'scheduled', 'trigger_url'")
    region: Optional[str] = Field(
        default=None, description="The region where the test run was executed")
    run_by: Optional[str] = Field(
        default=None, description="The name of the user who initiated the test run")
    environment_id: str = Field(
        description="The environment ID used for this test run")
    environment_name: Optional[str] = Field(
        default=None, description="The environment name used for this test run")
    requests: Optional[List[RequestResult]] = Field(
        default=None, description="List of individual request results within this test run")

    # Additional fields from the response
    agent: Optional[str] = Field(
        default=None,
        description="If test is executed on the private location. Only valid if region is null")
    parent_test_uuid: Optional[str] = Field(
        default=None, description="Parent test UUID in case of subtest execution only")
    test_run_url: Optional[str] = Field(
        default=None, description="Test run API URL")
    subtests_count: Optional[int] = Field(
        default=None, description="Number of subtests")
    subtests_passed: Optional[int] = Field(
        default=None, description="Number of subtests passed")
    subtests_failed: Optional[int] = Field(
        default=None, description="Number of subtests failed")
    subtests_others: Optional[int] = Field(
        default=None, description="Number of other subtest results")
    agent_expired: Optional[bool] = Field(
        default=None, description="Whether agent(private location) expired")
    subtest_detail: Optional[List[SubtestDetail]] = Field(
        default=None, description="Detailed subtest results")


class FailureDetails(BaseModel):
    """Failure details for bucket-level test run."""
    failed_test_runs: int = Field(
        alias="tests_failed", description="Number of failed test runs in the bucket-level test run")
    assertions_failed: int = Field(
        description="Total Number of assertions that failed across all the test runs")
    scripts_failed: int = Field(
        description="Total Number of scripts that failed across all the test runs")
    requests_failed: int = Field(
        description="Total Number of requests that failed across all the test runs")


class BucketLevelTestResult(BaseModel):
    """Bucket-level test run result."""
    bucket_level_test_run_id: str = Field(
        alias="uuid", description="Unique identifier for the bucket-level test run")
    status: str = Field(description="Status of the bucket-level test run")
    started_at: float = Field(
        description="Timestamp when the bucket-level test run started")
    total_test_runs: int = Field(
        description="Total number of test runs in the bucket")
    test_runs_passed: int = Field(
        description="Number of test runs that passed")
    result: Optional[str] = Field(
        default=None, description="Overall result of the bucket-level test run")
    total_requests: Optional[int] = Field(
        default=None, description="Total number of requests across all test runs")
    total_scripts: Optional[int] = Field(
        default=None, description="Total number of scripts across all test runs")
    total_assertions: Optional[int] = Field(
        default=None, description="Total number of assertions across all test runs")
    finished_at: Optional[float] = Field(
        default=None, description="Timestamp when the bucket-level test run finished")
    total_duration_in_sec: Optional[float] = Field(
        default=None, description="Total execution time of the bucket-level test run in seconds")
    bucket_key: str = Field(description="Key identifier for the bucket")
    bucket_name: str = Field(description="Name of the bucket")
    failure_details: Optional[FailureDetails] = Field(default=None,
                                                      description="Failure details when result is Failed")


class TestExecutionRuns(BaseModel):
    """Individual test run schema for trigger URL based test run."""
    test_run_id: str = Field(
        description="The unique identifier for the test run")
    test_id: str = Field(
        description="The unique identifier for the executed test")
    test_name: str = Field(description="The name of the test executed")
    region: Optional[str] = Field(
        default=None, description="The region i.e. public location where the test was executed")
    agent: Optional[str] = Field(
        default=None, description="The agent i.e. private Location where test is running")
    environment_id: str = Field(
        description="The environment ID used for this test run")
    test_run_url: str = Field(
        alias="api_test_run_url", description="The URL of the api to fetch the results of this test run")
    variables: Dict[str, Any] = Field(
        description="The variables used in the test run")


class TestExecution(BaseModel):
    """Test Execution model representing a test run summary."""
    bucket_level_test_run_id: Optional[str] = Field(
        default=None,
        alias="runs_id",
        description="The unique identifier for the bucket-level test run")
    bucket_level_test_run_url: Optional[str] = Field(
        alias="consolidated_test_results_url",
        description="The URL to view the consolidated results of the bucket-level test run")
    total_runs_started: int = Field(
        alias="runs_started", description="Total number of test runs started")
    total_runs_failed: int = Field(
        alias="runs_failed", description="Total number of test runs failed to start due to any issue/error")
    total_runs: int = Field(
        alias="runs_total",
        description="Total number of test runs. An individual test run can also be executed multiple "
                    "times if it is supposed to run on the multiple locations configured in the "
                    "environment.")
    test_results: List[TestExecutionRuns] = Field(
        alias="runs", description="List of details about the individual test runs started as part of this "
                                  "test run")

    class Config:
        extra = "ignore"
        populate_by_name = True
        by_alias = True
