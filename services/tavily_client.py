
import os
from typing import Optional

from dotenv import load_dotenv
from tavily import TavilyClient as _TavilyClient

from utils.logger import get_logger

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

logger = get_logger(__name__)

_client: Optional[_TavilyClient] = None


def get_tavily_client() -> _TavilyClient:
    global _client
    if _client is None:
        if not TAVILY_API_KEY:
            raise EnvironmentError(
                "TAVILY_API_KEY is not set. "
                "Add it to your .env file or export it in your shell."
            )
        _client = _TavilyClient(api_key=TAVILY_API_KEY)
    return _client


def live_search(
    query: str,
    domains: Optional[list[str]] = None,
    max_results: int = 5,
    search_depth: str = "basic",
) -> list[dict]:
    
    client = get_tavily_client()
    logger.info("Tavily live search | query=%s depth=%s", query, search_depth)

    kwargs: dict = {"search_depth": search_depth, "max_results": max_results}
    if domains:
        kwargs["include_domains"] = domains

    response = client.search(query, **kwargs)
    results = response.get("results", [])

    return [
        {
            "title": r.get("title"),
            "url": r.get("url"),
            "content": r.get("content"),
            "score": r.get("score"),
        }
        for r in results
    ]