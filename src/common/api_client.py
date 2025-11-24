"""
API Client for BlazeMeter API Monitoring
"""

import os
import platform
from typing import Optional, Callable
import httpx

from src.config.defaults import BZM_APIM_BASE_URL
from src.config.token import BzmApimToken
from src.config.version import __version__
from src.models import BaseResult


so = platform.system()       # "Windows", "Linux", "Darwin"
version = platform.version()  # kernel / build version
release = platform.release()  # ex. "10", "5.15.0-76-generic"
machine = platform.machine()  # ex. "x86_64", "AMD64", "arm64"

ua_part = f"{so} {release}; {machine}"


async def api_request(token: Optional[BzmApimToken], method: str, endpoint: str,
                      result_formatter: Callable = None,
                      result_formatter_params: Optional[dict] = None,
                      **kwargs) -> BaseResult:
    """
    Make an authenticated request to the BlazeMeter APIM APIs.
    Handles authentication errors gracefully.
    """
    if not token:
        return BaseResult(
            error="No API token. Set BZM_API_TEST_TOKEN env var with the token or BZM_API_TEST_TOKEN_FILE "
                  "with the file path or BZM_API_TEST_TOKEN secrets in docker catalog configuration.")

    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bearer {token}"
    headers["User-Agent"] = f"bzm-apitest-mcp/{__version__} ({ua_part})"

    timeout = httpx.Timeout(
        connect=15.0,
        read=60.0,
        write=15.0,
        pool=60.0
    )

    async with (httpx.AsyncClient(base_url=BZM_APIM_BASE_URL, timeout=timeout) as client):
        try:
            resp = await client.request(method, endpoint, headers=headers, **kwargs)
            resp.raise_for_status()
            response_dict = resp.json()
            result = response_dict.get("data", [])
            default_total = 0
            if not isinstance(
                    result, list):  # Generalize result always as a list
                result = [result]
                default_total = 1
            elif "total" not in response_dict:
                default_total = len(result)
            final_result = result_formatter(
                result, result_formatter_params) if result_formatter else result
            return BaseResult(
                result=final_result,
                error=response_dict.get("error", None),
                total=response_dict.get("total", default_total),
                has_more=response_dict.get("total", 0) - (
                    response_dict.get("skip", 0) + response_dict.get("limit", 0)) > 0,
                hint=kwargs.get("hint", [])
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                return BaseResult(
                    error=e.response.json().get("error", {}).get('message', 'Invalid Credentials')
                )
            elif e.response.status_code == 401:
                return BaseResult(
                    error="Unauthorized to perform this action"
                )
            raise
