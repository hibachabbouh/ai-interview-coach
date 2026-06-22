
from __future__ import annotations
from typing import Literal

from tools.web_search_tool import WebSearchTool
from tools.base_tool import BaseTool, ToolResult
from utils.logger import get_logger

logger = get_logger(__name__)

BEHAVIORAL_DOMAINS: list[str] = [
    "themuse.com",
    "glassdoor.com",
    "indeed.com",
    "linkedin.com",
    "hbr.org",
    "biginterview.com",
]

BehavioralCategory = Literal[
    "general",
    "leadership",
    "teamwork",
    "conflict",
    "failure",
    "achievement",
    "motivation",
    "data_science",  
]

_CATEGORY_HINTS: dict[BehavioralCategory, str] = {
    "general":      "behavioral interview questions STAR method examples",
    "leadership":   "leadership behavioral interview questions examples answers",
    "teamwork":     "teamwork collaboration behavioral interview STAR",
    "conflict":     "conflict resolution behavioral interview question answer",
    "failure":      "failure mistake behavioral interview tell me about a time",
    "achievement":  "achievement success behavioral interview STAR example",
    "motivation":   "motivation passion behavioral interview why data science",
    "data_science": "data scientist behavioral interview questions examples answers",
}


class BehavioralTool(BaseTool):

    name = "behavioral_questions"

    def __init__(self, max_results: int = 6) -> None:
        self._searcher = WebSearchTool(
            include_domains=BEHAVIORAL_DOMAINS,
            max_results=max_results,
            search_depth="basic",
        )
        self._glassdoor = WebSearchTool(
            include_domains=["glassdoor.com"],
            max_results=4,
        )

    

    def run(self, query: str, category: BehavioralCategory = "general", **kwargs) -> ToolResult:
        hint     = _CATEGORY_HINTS.get(category, "")
        enriched = f"{query} {hint}".strip()

        logger.info("BehavioralTool | category=%s query=%r", category, query)

        result = self._searcher.run(enriched)
        result.tool  = self.name
        result.query = query
        return result

   

    def get_by_category(self, category: BehavioralCategory) -> ToolResult:
       
        hint = _CATEGORY_HINTS.get(category, "behavioral interview questions")
        result = self._searcher.run(hint)
        result.tool  = self.name
        result.query = category
        return result

    def get_star_example(self, situation: str) -> ToolResult:
        
        query = f"STAR method example answer: {situation}"
        return self.run(query, category="general")

    def get_company_culture(self, company: str, role: str = "") -> ToolResult:
        
        query = f"{company} {role} interview behavioral questions glassdoor".strip()
        logger.info("BehavioralTool | company=%s role=%s", company, role)

        result = self._glassdoor.run(query)
        result.tool  = self.name
        result.query = f"{company} / {role}" if role else company
        return result

    def get_ds_specific(self) -> ToolResult:
        
        return self.run(
            "data scientist machine learning behavioral interview",
            category="data_science",
        )