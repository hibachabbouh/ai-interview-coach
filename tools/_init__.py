
from tools.base_tool          import BaseTool, ToolResult
from tools.web_search_tool    import WebSearchTool
from tools.leetcode_tool      import LeetcodeTool
from tools.github_questions_tool import GithubQuestionsTool
from tools.ml_docs_tool       import MlDocsTool
from tools.behavioral_tool    import BehavioralTool


class ToolRegistry:
   

    def __init__(self) -> None:
        self.web       = WebSearchTool(max_results=5)
        self.leetcode  = LeetcodeTool(max_results=6)
        self.github    = GithubQuestionsTool(max_results=6)
        self.ml_docs   = MlDocsTool(mode="core", max_results=5)
        self.behavioral = BehavioralTool(max_results=6)

    def get_all_tools(self) -> list[BaseTool]:
        return [self.web, self.leetcode, self.github, self.ml_docs, self.behavioral]


__all__ = [
    "BaseTool",
    "ToolResult",
    "WebSearchTool",
    "LeetcodeTool",
    "GithubQuestionsTool",
    "MlDocsTool",
    "BehavioralTool",
    "ToolRegistry",
]