
from __future__ import annotations
from typing import Literal

from tools.web_search_tool import WebSearchTool
from tools.base_tool import BaseTool, ToolResult
from utils.logger import get_logger

logger = get_logger(__name__)


_CORE_ML_DOMAINS: list[str] = [
    "scikit-learn.org",
    "towardsdatascience.com",
    "machinelearningmastery.com",
    "neptune.ai",
]

_RESEARCH_DOMAINS: list[str] = [
    "arxiv.org",
    "paperswithcode.com",
]

_ALL_DOMAINS: list[str] = _CORE_ML_DOMAINS + _RESEARCH_DOMAINS

Topic = Literal["algorithms", "statistics", "deep_learning", "mlops", "sql", "general"]
_TOPIC_HINTS: dict[Topic, str] = {
    "algorithms":    "machine learning algorithm explanation interview",
    "statistics":    "statistics probability data science interview concept",
    "deep_learning": "neural network deep learning architecture interview",
    "mlops":         "MLOps model deployment pipeline interview best practices",
    "sql":           "SQL data manipulation interview question",
    "general":       "data science interview concept explanation",
}


class MlDocsTool(BaseTool):

    name = "ml_docs"

    def __init__(
        self,
        mode: Literal["core", "research", "all"] = "core",
        max_results: int = 5,
    ) -> None:
        if mode == "core":
            domains = _CORE_ML_DOMAINS
        elif mode == "research":
            domains = _RESEARCH_DOMAINS
        else:
            domains = _ALL_DOMAINS

        self._mode = mode
        self._searcher = WebSearchTool(
            include_domains=domains,
            max_results=max_results,
            search_depth="basic",
        )
        self._adv_searcher = WebSearchTool(
            include_domains=domains,
            max_results=max_results,
            search_depth="advanced",   
        )


    def run(self, query: str, topic: Topic = "general", **kwargs) -> ToolResult:
        hint    = _TOPIC_HINTS.get(topic, "")
        enriched = f"{query} {hint}".strip()

        logger.info("MlDocsTool | mode=%s topic=%s query=%r", self._mode, topic, query)

        searcher = self._adv_searcher if self._mode == "research" else self._searcher
        result   = searcher.run(enriched)
        result.tool  = self.name
        result.query = query
        return result

    def get_concept(self, concept: str) -> ToolResult:
        return self.run(f"explain {concept}", topic="general")

    def get_sklearn_api(self, query: str) -> ToolResult:
        result = WebSearchTool(
            include_domains=["scikit-learn.org"],
            max_results=4,
        ).run(query)
        result.tool  = self.name
        result.query = query
        return result

    def research(self, query: str) -> ToolResult:
        result = self._adv_searcher.run(
            f"{query} arxiv paper abstract",
            include_domains=_RESEARCH_DOMAINS,
        )
        result.tool  = self.name
        result.query = query
        return result

    def get_best_practices(self, topic: str) -> ToolResult:
        return self.run(f"{topic} best practices tips", topic="general")