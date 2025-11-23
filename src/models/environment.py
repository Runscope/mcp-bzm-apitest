from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field, model_validator


class EmailSettings(BaseModel):
    """Email settings model representing email notification settings."""
    recipients: Optional[List[Dict[Any, Any]]] = Field(
        default=None, description="List of email recipients for notifications")


class Environment(BaseModel):
    """Environment model representing a test environment."""
    environment_id: str = Field(
        alias="id", description="Unique environment identifier")
    test_id: str = Field(
        description="The test unique id this environment belongs to")
    name: str = Field(description="The name of the environment")
    parent_environment_id: Optional[str] = Field(
        default=None, description="The parent environment id if this environment is inherited from another "
                                  "environment")
    initial_variables: Optional[Dict[str, str]] = Field(
        default=None, description="The initial environment variables")
    retry_on_failure: bool = Field(
        description="Whether to retry the test on failure once again is test source is scheduled")
    script: Optional[str] = Field(
        default=None, description="The initial script that will be run before the execution of test steps")
    webhooks: Optional[List] = Field(
        default=None, description="List of webhooks URLs to be called for notifications after test run "
                                  "completion")
    integrations: Optional[list[Dict]] = Field(
        default=None, description="List of 3rd party integrations like Slack, MS Teams configured for this"
                                  " environment")
    emails: Optional[EmailSettings] = Field(
        default=None, description="Email notifications enabled for this environment")
    preserve_cookies: bool = Field(
        description="Whether to preserve cookies between test steps")
    stop_on_failure: bool = Field(
        description="Whether to stop the test on the first failure and not execute the remaining steps")
    verify_ssl: bool = Field(
        description="Whether to verify SSL certificates for HTTPS requests")
    http_version_support: str = Field(description="HTTP version support")
    force_h2c: bool = Field(
        description="Whether to force HTTP/2 cleartext (h2c) connections")
    regions: list[str] = Field(
        description="List of cloud regions from which the test will be executed")
    remote_agents: list[Dict[str, str]] = Field(
        default=None, description="List of remote agents configuration")
    headers: Optional[Dict[Any, Any]] = Field(
        default=None, description="Headers to be included in all requests")
    pre_request_scripts: Optional[list[str]] = Field(
        default=None, description="List of pre request scripts to be executed")
    post_response_scripts: Optional[list[str]] = Field(
        default=None, description="List of post response scripts to be executed")
    is_client_certificate_used: Optional[bool] = Field(
        default=False, description="Indicates whether client certificate authentication is used in this"
                                   " environment")
    is_auth_enabled: Optional[bool] = Field(
        default=False, description="Indicates whether any authentication is enabled in this environment")
    auth_type: Optional[str] = Field(
        default=None, description="Type of authentication used in this environment,"
                                  " e.g. 'basic', 'oauth1' and 'oauth2' or client certificate")

    @model_validator(mode='before')
    @classmethod
    def preprocess_env(cls, data):
        """Preprocess environment data before validation."""
        if ("client_certificate" in data or
                ("auth" in data and data["auth"].get("auth_type") == "client_certificate")):
            data['is_client_certificate_used'] = True
            data.pop('client_certificate')

        if "auth" in data and isinstance(data["auth"], dict):
            auth_type = data["auth"].get("auth_type")
            if auth_type:
                data["is_auth_enabled"] = True
                data["auth_type"] = auth_type
                data.pop('auth')
        return data
