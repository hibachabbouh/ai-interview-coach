

from __future__ import annotations
import os
import time
from typing import Any

from dotenv import load_dotenv
from tavily import TavilyClient

from tools.base_tool import BaseTool, ToolResult
from utils.logger import get_logger

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
ENABLE_SEARCH_CACHE = os.getenv("ENABLE_SEARCH_CACHE", "true").lower() in ("true", "1", "yes")

logger = get_logger(__name__)


class WebSearchTool(BaseTool):

    name = "web_search"

    ALWAYS_ALLOWED: list[str] = [
        "github.com",
        "stackoverflow.com",
        "medium.com",
        "dev.to",
        "reddit.com",
    ]

    def __init__(
        self,
        include_domains: list[str] | None = None,
        max_results: int = 5,
        search_depth: str = "basic",
        use_cache: bool = True,
    ) -> None:
        if not TAVILY_API_KEY:
            raise EnvironmentError(
                "TAVILY_API_KEY is not set. "
                "Add it to your .env file or export it in your shell."
            )
        self._client = TavilyClient(api_key=TAVILY_API_KEY)
        self.include_domains = include_domains
        self.max_results = max_results
        self.search_depth = search_depth

        self.use_cache = use_cache and ENABLE_SEARCH_CACHE
        self._cache = None
        if self.use_cache:
            try:
                from services.search_cache import SearchCache
                self._cache = SearchCache()
            except Exception as exc:
                logger.warning("SearchCache failed to initialize: %s. Caching will be disabled.", exc)
                self.use_cache = False


    def run(
        self,
        query: str,
        include_domains: list[str] | None = None,
        use_cache: bool | None = None,
        **kwargs,
    ) -> ToolResult:
        domains = include_domains or self.include_domains
        enable_cache = use_cache if use_cache is not None else self.use_cache

        if enable_cache and self._cache is not None:
            t0 = time.perf_counter()
            try:
                cached = self._cache.lookup(
                    query=query,
                    domains=domains,
                    max_results=self.max_results,
                    search_depth=self.search_depth,
                )
                if cached is not None:
                    latency_ms = (time.perf_counter() - t0) * 1000
                    logger.info("WebSearch Cache HIT | query=%r | latency=%.2fms", query, latency_ms)
                    return ToolResult(
                        success=True,
                        tool=self.name,
                        query=query,
                        results=cached,
                    )
            except Exception as exc:
                logger.warning("WebSearch cache lookup failed: %s. Falling back to live search.", exc)

        t0 = time.perf_counter()
        logger.info("WebSearch live search | query=%r domains=%s", query, domains)
        try:
            response: dict[str, Any] = self._client.search(
                query=query,
                search_depth=self.search_depth,
                max_results=self.max_results,
                include_domains=domains,
                include_answer=False,
                include_raw_content=False,
            )

            results = [
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "snippet": r.get("content", ""),
                    "score": r.get("score", 0.0),
                }
                for r in response.get("results", [])
            ]

            latency_ms = (time.perf_counter() - t0) * 1000
            logger.debug("WebSearch | %d results returned | latency=%.2fms", len(results), latency_ms)

            if enable_cache and self._cache is not None:
                try:
                    self._cache.save(
                        query=query,
                        results_list=results,
                        domains=domains,
                        max_results=self.max_results,
                        search_depth=self.search_depth,
                    )
                except Exception as exc:
                    logger.warning("WebSearch failed to save to cache: %s", exc)

            return ToolResult(success=True, tool=self.name, query=query, results=results)

        except Exception as exc:
            logger.error("WebSearch error | %s", exc)
            return ToolResult(success=False, tool=self.name, query=query, error=str(exc))