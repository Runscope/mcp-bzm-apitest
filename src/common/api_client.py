"""
API Client for BlazeMeter API Monitoring
"""

import os
import platform
from typing import Optional, Dict, Any
import httpx

from src.config.defaults import BZM_APIM_BASE_URL
from src.config.version import __version__


class APIClient:
    """
    HTTP client for BlazeMeter API Monitoring API.
    """

    def __init__(self, api_token: Optional[str] = None):
        """
        Initialize the API client.

        Args:
            api_key: API key for authentication (defaults to BZM_API_KEY env var)
        """
        self.api_token = api_token or os.getenv("BZM_APIM_TOKEN")
        self.base_url = BZM_APIM_BASE_URL

        if not self.api_token:
            raise ValueError("API token is required. Set BZM_APIM_TOKEN environment variable with file path or BZM_APIM_TOKEN secret in docker catalog configuration.")

        so = platform.system()  # "Windows", "Linux", "Darwin"
        version = platform.version()  # kernel / build version
        release = platform.release()  # ex. "10", "5.15.0-76-generic"
        machine = platform.machine()  # ex. "x86_64", "AMD64", "arm64"

        ua_part = f"{so} {release}; {machine}"

        timeout = httpx.Timeout(
            connect=15.0,
            read=60.0,
            write=15.0,
            pool=60.0
        )

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
                "User-Agent": f"MCP-BZM-APIM/{__version__} ({ua_part})"
            },
            timeout=timeout
        )

    async def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a GET request."""
        response = await self.client.get(path, params=params)
        response.raise_for_status()
        return response.json()

    async def post(self, path: str, json: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a POST request."""
        response = await self.client.post(path, json=json)
        response.raise_for_status()
        return response.json()

    async def put(self, path: str, json: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a PUT request."""
        response = await self.client.put(path, json=json)
        response.raise_for_status()
        return response.json()

    async def delete(self, path: str) -> Dict[str, Any]:
        """Make a DELETE request."""
        response = await self.client.delete(path)
        response.raise_for_status()
        return response.json()

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

