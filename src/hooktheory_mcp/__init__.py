"""
Hooktheory MCP Server

A Model Context Protocol server that enables agents to query the Hooktheory API
for chord progression generation, song analysis, and music theory data.
"""

import asyncio
import logging
import os
import time
from typing import Any, Dict, Optional

import httpx
from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("Hooktheory MCP Server")


class RateLimiter:
    """Simple rate limiter with exponential backoff."""

    def __init__(self, max_requests_per_second: float = 2.0):
        self.max_requests_per_second = max_requests_per_second
        self.min_interval = 1.0 / max_requests_per_second
        self.last_request_time = 0.0
        self.backoff_delay = 0.0
        self.consecutive_failures = 0

    async def wait(self):
        """Wait if necessary to respect rate limits."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        # Apply backoff delay if we have consecutive failures
        total_delay = max(self.min_interval - time_since_last, self.backoff_delay)

        if total_delay > 0:
            await asyncio.sleep(total_delay)

        self.last_request_time = time.time()

    def on_success(self):
        """Reset backoff on successful request."""
        self.consecutive_failures = 0
        self.backoff_delay = 0.0

    def on_failure(self):
        """Increase backoff delay on failed request."""
        self.consecutive_failures += 1
        # Exponential backoff: 1s, 2s, 4s, 8s, max 60s
        self.backoff_delay = min(60.0, 2 ** (self.consecutive_failures - 1))


class HooktheoryClient:
    """Client for interacting with the Hooktheory API with OAuth 2 authentication."""

    def __init__(self, base_url: str = "https://www.hooktheory.com/api"):
        self.base_url = base_url
        self.trends_base_url = f"{base_url}/trends"
        self.username = os.getenv("HOOKTHEORY_USERNAME")
        self.password = os.getenv("HOOKTHEORY_PASSWORD")

        # Token management
        self.access_token: Optional[str] = None
        self.user_id: Optional[int] = None
        self.token_expires_at: Optional[float] = None

        # Rate limiting
        self.rate_limiter = RateLimiter(
            max_requests_per_second=1.5
        )  # Conservative rate

    async def _authenticate(self) -> Dict[str, Any]:
        """Authenticate with Hooktheory API using username/password."""
        if not self.username or not self.password:
            raise ValueError(
                "HOOKTHEORY_USERNAME and HOOKTHEORY_PASSWORD environment variables are required"
            )

        auth_url = f"{self.base_url}/users/auth"
        auth_data = {"username": self.username, "password": self.password}

        async with httpx.AsyncClient() as client:
            try:
                logger.info("Authenticating with Hooktheory API")
                response = await client.post(auth_url, json=auth_data)
                response.raise_for_status()

                auth_response = response.json()
                logger.info(
                    f"Authentication successful for user: {auth_response.get('username')}"
                )
                return auth_response

            except httpx.HTTPStatusError as e:
                logger.error(f"Authentication failed: HTTP {e.response.status_code}")
                if e.response.status_code == 401:
                    raise ValueError("Invalid username or password")
                raise
            except httpx.RequestError as e:
                logger.error(f"Request error during authentication: {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error during authentication: {e}")
                raise

    async def _ensure_authenticated(self):
        """Ensure we have a valid access token."""
        # Check if we already have a valid token
        if (
            self.access_token
            and self.token_expires_at
            and time.time() < self.token_expires_at
        ):
            return

        # Authenticate and get new token
        auth_response = await self._authenticate()
        self.access_token = auth_response["activkey"]
        self.user_id = auth_response.get("id")

        # Set expiration time (assume 24 hours if not specified)
        self.token_expires_at = time.time() + (24 * 60 * 60)

        logger.info("Access token updated successfully")

    async def _make_request(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make an authenticated request to the Hooktheory API with rate limiting."""

        # Ensure we have a valid token
        await self._ensure_authenticated()

        # Apply rate limiting
        await self.rate_limiter.wait()

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "User-Agent": "Hooktheory-MCP-Server/0.2.0",
            "Content-Type": "application/json",
        }

        url = f"{self.trends_base_url}/{endpoint}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                logger.debug(f"Making request to {url} with params: {params}")
                response = await client.get(url, headers=headers, params=params or {})

                if response.status_code == 429:
                    # Rate limited - apply backoff
                    self.rate_limiter.on_failure()
                    retry_after = int(response.headers.get("Retry-After", "60"))
                    logger.warning(
                        f"Rate limited. Waiting {retry_after} seconds before retry"
                    )
                    await asyncio.sleep(retry_after)

                    # Retry once after rate limit
                    await self.rate_limiter.wait()
                    response = await client.get(
                        url, headers=headers, params=params or {}
                    )

                if response.status_code == 401:
                    # Token might be expired, force re-authentication
                    logger.info("Received 401, forcing re-authentication")
                    self.access_token = None
                    self.token_expires_at = None
                    await self._ensure_authenticated()

                    # Update headers with new token
                    headers["Authorization"] = f"Bearer {self.access_token}"

                    # Retry with new token
                    await self.rate_limiter.wait()
                    response = await client.get(
                        url, headers=headers, params=params or {}
                    )

                response.raise_for_status()
                self.rate_limiter.on_success()

                result = response.json()
                logger.debug(
                    f"Request successful: {len(str(result))} characters returned"
                )
                return result

            except httpx.HTTPStatusError as e:
                self.rate_limiter.on_failure()
                logger.error(f"HTTP {e.response.status_code} error calling {url}: {e}")
                raise
            except httpx.RequestError as e:
                self.rate_limiter.on_failure()
                logger.error(f"Request error calling {url}: {e}")
                raise
            except Exception as e:
                self.rate_limiter.on_failure()
                logger.error(f"Unexpected error calling {url}: {e}")
                raise


# Create a global client instance
hooktheory_client = HooktheoryClient()


@mcp.tool()
async def get_chord_progressions(
    cp: str,
    key: Optional[str] = None,
    mode: Optional[str] = None,
    artist: Optional[str] = None,
    song: Optional[str] = None,
) -> str:
    """
    Get chord progressions and related songs from Hooktheory.

    Args:
        cp: Chord progression in Roman numeral notation (e.g., "1,5,6,4")
        key: Musical key (e.g., "C", "Am")
        mode: Scale mode (e.g., "major", "minor")
        artist: Filter by artist name
        song: Filter by song title

    Returns:
        JSON string containing chord progression data and similar songs
    """
    try:
        params: Dict[str, Any] = {"cp": cp}
        if key:
            params["key"] = key
        if mode:
            params["mode"] = mode
        if artist:
            params["artist"] = artist
        if song:
            params["song"] = song

        result = await hooktheory_client._make_request("songs", params)
        return str(result)

    except Exception as e:
        error_msg = f"Error fetching chord progressions: {str(e)}"
        logger.error(error_msg)
        return error_msg


@mcp.tool()
async def analyze_song(artist: str, song: str) -> str:
    """
    Analyze a specific song to get its chord progression, key, and music theory data.

    Args:
        artist: Artist name
        song: Song title

    Returns:
        JSON string containing song analysis including chords, key, and structure
    """
    try:
        params: Dict[str, Any] = {"artist": artist, "song": song}

        result = await hooktheory_client._make_request("songs/search", params)
        return str(result)

    except Exception as e:
        error_msg = f"Error analyzing song '{song}' by {artist}: {str(e)}"
        logger.error(error_msg)
        return error_msg


@mcp.tool()
async def get_popular_progressions(
    key: Optional[str] = None, mode: Optional[str] = None, limit: int = 20
) -> str:
    """
    Get the most popular chord progressions from the Hooktheory database.

    Args:
        key: Filter by musical key (e.g., "C", "Am")
        mode: Filter by scale mode ("major" or "minor")
        limit: Maximum number of results to return (default: 20)

    Returns:
        JSON string containing popular chord progressions and their usage statistics
    """
    try:
        params: Dict[str, Any] = {"limit": limit}
        if key:
            params["key"] = key
        if mode:
            params["mode"] = mode

        result = await hooktheory_client._make_request("nodes", params)
        return str(result)

    except Exception as e:
        error_msg = f"Error fetching popular progressions: {str(e)}"
        logger.error(error_msg)
        return error_msg


@mcp.tool()
async def find_similar_songs(
    artist: str, song: str, similarity_threshold: float = 0.7
) -> str:
    """
    Find songs with similar chord progressions to a given song.

    Args:
        artist: Artist name of the reference song
        song: Title of the reference song
        similarity_threshold: Similarity score threshold (0.0 to 1.0)

    Returns:
        JSON string containing similar songs and their similarity scores
    """
    try:
        # Search for similar progressions (this would require the actual API structure)
        params: Dict[str, Any] = {
            "artist": artist,
            "song": song,
            "threshold": similarity_threshold,
        }

        result = await hooktheory_client._make_request("similar", params)
        return str(result)

    except Exception as e:
        error_msg = f"Error finding songs similar to '{song}' by {artist}: {str(e)}"
        logger.error(error_msg)
        return error_msg


@mcp.tool()
async def generate_progression(
    key: str = "C", mode: str = "major", length: int = 4, style: Optional[str] = None
) -> str:
    """
    Generate a chord progression based on music theory patterns from Hooktheory data.

    Args:
        key: Starting key for the progression (e.g., "C", "Am")
        mode: Scale mode ("major" or "minor")
        length: Number of chords in the progression
        style: Musical style/genre hint (e.g., "pop", "rock", "jazz")

    Returns:
        JSON string containing the generated chord progression with probabilities
    """
    try:
        params: Dict[str, Any] = {"key": key, "mode": mode, "length": length}
        if style:
            params["style"] = style

        result = await hooktheory_client._make_request("generate", params)
        return str(result)

    except Exception as e:
        error_msg = f"Error generating chord progression: {str(e)}"
        logger.error(error_msg)
        return error_msg


def main():
    """Main entry point for the MCP server."""
    import argparse

    parser = argparse.ArgumentParser(description="Hooktheory MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        help="Transport mechanism (default: stdio)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for web-based transports (default: 8000)",
    )

    args = parser.parse_args()

    # Check for authentication credentials
    username = os.getenv("HOOKTHEORY_USERNAME")
    password = os.getenv("HOOKTHEORY_PASSWORD")

    if not username or not password:
        logger.warning(
            "Authentication credentials not found. Please set "
            "HOOKTHEORY_USERNAME and HOOKTHEORY_PASSWORD environment variables"
        )
        print("Warning: Authentication required. Please set:")
        print("  - HOOKTHEORY_USERNAME")
        print("  - HOOKTHEORY_PASSWORD")
    else:
        logger.info("Using OAuth 2.0 authentication with username/password")

    if args.transport == "stdio":
        print("Starting Hooktheory MCP Server with stdio transport")
        mcp.run()
    elif args.transport == "sse":
        print("Starting Hooktheory MCP Server with SSE transport")
        mcp.run(transport="sse")
    elif args.transport == "streamable-http":
        print("Starting Hooktheory MCP Server with streamable-http transport")
        mcp.run(transport="streamable-http")
    else:
        print("Starting Hooktheory MCP Server with default stdio transport")
        mcp.run()


if __name__ == "__main__":
    main()
