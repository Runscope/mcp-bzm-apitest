"""
Schedule models for BlazeMeter API Monitoring
"""

from typing import Optional, Dict
from pydantic import BaseModel, Field


class CreateSchedule(BaseModel):
    """Schedule model for creating a schedule"""
    note: Optional[str] = Field(alias="description",
                                       default=None, description="The description of the schedule")
    interval: str = Field(
	    description="The interval at which the test is scheduled to run. possible values are 1m, 5m, 1h, 6h etc. where m represents minutes and h represents hours")
    environment_id: str = Field(
	    description="The unique identifier for the environment which this test schedule should be using during the test run")


class Schedule(BaseModel):
    """Model for schedules"""
    schedule_id: str = Field(alias="id", description="The unique identifier for the schedule. Also known as schedule_id")
    description: Optional[str] = Field(alias="note",
        default=None, description="The description of the schedule")
    interval: str = Field(
        description="The interval at which the test is scheduled to run. possible values are 1m, 5m, 1h, 6h etc. where m represents minutes and h represents hours")
    environment_id: str = Field(description="The unique identifier for the environment which this test schedule should be using during the test run")

    class Config:
        extra = "ignore"
