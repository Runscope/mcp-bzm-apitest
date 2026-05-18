import httpx


def http_error_message(e: httpx.HTTPStatusError) -> str:
    """Convert an HTTP error into a categorized, LLM-friendly message without exposing raw tracebacks."""
    status = e.response.status_code
    if status in (401, 403):
        return (
            f"Authentication error (HTTP {status}): Your API token does not have permission to perform "
            "this action. Verify your BZM_API_TEST_TOKEN is valid and has the required permissions."
        )
    elif status == 404:
        return (
            "Not found (HTTP 404): The requested resource does not exist. "
            "Check that the IDs you provided are correct."
        )
    elif status == 429:
        return (
            "Rate limited (HTTP 429): Too many requests to the BlazeMeter API. "
            "Wait before retrying this action."
        )
    elif status >= 500:
        return (
            f"BlazeMeter API server error (HTTP {status}): This is a system issue on BlazeMeter's side, "
            "not a problem with your request. Try again later."
        )
    return f"HTTP {status} error from BlazeMeter API."


UNEXPECTED_ERROR_MESSAGE = (
    "An unexpected error occurred while communicating with the BlazeMeter API. "
    "This may be a network connectivity issue. "
    "If the problem persists, report it at https://github.com/Runscope/mcp-bzm-apitest/issues"
)
