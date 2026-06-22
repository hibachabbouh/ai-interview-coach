
from __future__ import annotations
from tools.web_search_tool import WebSearchTool
from tools.base_tool import BaseTool, ToolResult
from utils.logger import get_logger

logger = get_logger(__name__)

GITHUB_DOMAINS: list[str] = [
    "github.com",
    "raw.githubusercontent.com",
    "gist.github.com",
]


_TOP_REPOS: list[str] = [
    "donnemartin/system-design-primer",
    "alexeygrigorev/data-science-interviews",
    "khangich/machine-learning-interview",
    "DataTalksClub/data-engineering-zoomcamp",
    "andrewekhalel/MLQuestions",
]


class GithubQuestionsTool(BaseTool):
   

    name = "github_questions"

    _QUERY_SUFFIX = "site:github.com interview questions"

    def __init__(self, max_results: int = 6) -> None:
        self._searcher = WebSearchTool(
            include_domains=GITHUB_DOMAINS,
            max_results=max_results,
            search_depth="basic",
        )

    def run(self, query: str, **kwargs) -> ToolResult:
        enriched = f"{query} interview questions github repository"
        logger.info("GithubQuestionsTool | query=%r", query)

        result = self._searcher.run(enriched)
        result.tool  = self.name
        result.query = query
        return result

    def search_repo(self, repo_path: str, topic: str = "") -> ToolResult:
        query = f"github.com/{repo_path} {topic}".strip()
        logger.info("GithubQuestionsTool | repo=%s topic=%r", repo_path, topic)

        result = self._searcher.run(query)
        result.tool  = self.name
        result.query = f"{repo_path} / {topic}" if topic else repo_path
        return result

    def get_data_science_questions(self, topic: str) -> ToolResult:
        
        query = (
            f"data science {topic} interview questions "
            "github awesome list"
        )
        return self.run(query)