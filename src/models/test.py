"""
Test models for BlazeMeter API Monitoring
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class CreatedBy(BaseModel):
    """User who created the test."""

    id: str = Field(description="User who created this test. Also known as user_id")
    email: str = Field(description="Email address of the user who created this test")
    name: str = Field(description="Name of the user who created this test")


class LastTestRun(BaseModel):
    """Last test run result. Only keeping test_run_id and status for brevity.
    Client(AI) can use the test_run_id to fetch the full test result details if needed.
    """

    id: str = Field(description="The unique identifier for the test run. Also known as test_run_id")
    status: str = Field(
        description="The status of the test run. Possible values: 'completed', 'error', 'expired', "
        "'canceled'"
    )


class TestStepMini(BaseModel):
    """Test Step object. Only keeping test step id and step type for brevity.
    Client(AI) can use the step id to fetch the full test step details if needed.
    """

    id: str = Field(description="The unique identifier for the test step. Also known as step_id")
    step_type: str = Field(
        description="The type of the test step. Possible values: 'request', 'pause', 'conditional', "
        "'conditional-loop', 'subtest' and 'inbound'"
    )


class Test(BaseModel):
    """API Test basic model with essential fields only.

    This model intentionally excludes fields like environments, schedules,
    and detailed step configurations which can be fetched via separate APIs:
    - GET /buckets/{bucket_key}/tests/{test_id}/environments
    - GET /buckets/{bucket_key}/tests/{test_id}/schedules
    - GET /buckets/{bucket_key}/tests/{test_id}/steps/{step_id}
    """

    test_id: str = Field(
        alias="id", description="The unique identifier for the test. Also known as test_id"
    )
    name: str = Field(description="The name of the test")
    description: Optional[str] = Field(default=None, description="The description of the test")
    default_environment_id: str = Field(description="The default environment ID")
    trigger_url: str = Field(description="The trigger URL. It is used to start test runs via API")
    created_by: CreatedBy
    created_at: float = Field(description="The timestamp when the test was created (Unix timestamp)")
    step_count: int = Field(default=0, description="Total steps count in the test")
    last_run_created_at: Optional[float] = Field(
        default=None, description="The timestamp when the test was last run (Unix timestamp)"
    )
    last_run: Optional[LastTestRun] = Field(default=None, description="Last test run result")

    class Config:
        extra = "ignore"


class ResponseTimePoint(BaseModel):
    """A single point in the response times timeseries data."""

    timestamp: int = Field(description="Unix timestamp for this data point")
    avg_response_time_ms: float = Field(
        description="Average response time in milliseconds at this timestamp"
    )
    success_ratio: float = Field(description="Success ratio at this timestamp (0.0 to 1.0)")


class PeriodMetrics(BaseModel):
    """Metrics for a specific time period."""

    total_test_runs: Optional[float] = Field(
        default=None, description="Total number of test runs in the period"
    )
    response_time_50th_percentile: Optional[float] = Field(
        default=None, description="50th percentile (median) response time in milliseconds"
    )
    response_time_95th_percentile: Optional[float] = Field(
        default=None, description="95th percentile response time in milliseconds"
    )
    response_time_99th_percentile: Optional[float] = Field(
        default=None, description="99th percentile response time in milliseconds"
    )


class TestMetrics(BaseModel):
    """Model representing test metrics data from API Monitoring."""

    response_times: List[ResponseTimePoint] = Field(
        description="Time-series data points for response times and success ratios"
    )
    timeframe: str = Field(
        description="The timeframe for the metrics. Possible values: 'hour', 'day', 'week', 'month'"
    )
    this_time_period: PeriodMetrics = Field(description="Aggregated metrics for the current time period")
    change_from_last_period: PeriodMetrics = Field(
        description="Change in metrics compared to the previous period. Values can be null if no previous"
        " data exists"
    )
    region: str = Field(
        description="The region filter applied. Use 'all' for all regions or specific region code"
    )
    environment_id: str = Field(
        alias="environment_uuid",
        description="The environment filter applied.Use 'all' for all environments or specific environment",
    )

    class Config:
        extra = "ignore"
