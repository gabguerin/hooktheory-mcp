"""
Hooktheory MCP Server

A Model Context Protocol server that enables agents to query the Hooktheory API
for chord progression generation, song analysis, and music theory data.
"""

import logging
import os
from typing import Any, Dict, Optional

import httpx
from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the MCP server
mcp = FastMCP("Hooktheory MCP Server")


class HooktheoryClient:
    """Client for interacting with the Hooktheory API."""

    def __init__(self, base_url: str = "https://www.hooktheory.com/api/trends"):
        self.base_url = base_url
        self.api_key = os.getenv("HOOKTHEORY_API_KEY")

    async def _make_request(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make an authenticated request to the Hooktheory API."""
        if not self.api_key:
            raise ValueError("HOOKTHEORY_API_KEY environment variable is required")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "Hooktheory-MCP-Server/0.1.0",
        }

        url = f"{self.base_url}/{endpoint}"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, params=params or {})
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"HTTP error calling {url}: {e}")
                raise
            except Exception as e:
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
        params: Dict[str, Any] = {"artist": artist, "song": song, "threshold": similarity_threshold}

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
        "--port", type=int, default=8000, help="Port for web-based transports (default: 8000)"
    )

    args = parser.parse_args()

    # Check for API key
    if not os.getenv("HOOKTHEORY_API_KEY"):
        logger.warning(
            "HOOKTHEORY_API_KEY environment variable not set. API calls will fail."
        )
        print("Warning: Please set HOOKTHEORY_API_KEY environment variable")

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
