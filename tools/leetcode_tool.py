
from __future__ import annotations
from tools.web_search_tool import WebSearchTool
from tools.base_tool import BaseTool, ToolResult
from utils.logger import get_logger

logger = get_logger(__name__)


LEETCODE_DOMAINS: list[str] = [
    "github.com",           
    "geeksforgeeks.org",    
    "leetcode.com",         
    "neetcode.io",         
]


class LeetcodeTool(BaseTool):

    name = "leetcode_questions"

    _QUERY_SUFFIX = "coding interview question solution explanation"

    def __init__(self, max_results: int = 6) -> None:
        self._searcher = WebSearchTool(
            include_domains=LEETCODE_DOMAINS,
            max_results=max_results,
            search_depth="basic",
        )

    def run(self, query: str, **kwargs) -> ToolResult:
        enriched_query = f"{query} {self._QUERY_SUFFIX}"
        logger.info("LeetcodeTool | query=%r", query)

        result = self._searcher.run(enriched_query)
        result.tool  = self.name
        result.query = query          
        return result

    def get_questions_for_role(self, role: str, topic: str = "") -> ToolResult:
        
        query = f"{role} {topic} interview coding questions".strip()
        return self.run(query)

    def get_company_questions(self, company: str, role: str = "") -> ToolResult:
        query = f"{company} {role} interview questions github".strip()
        return self.run(query)