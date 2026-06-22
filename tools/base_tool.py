

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolResult:

    success:  bool
    tool:     str                      
    query:    str                        
    results:  list[dict[str, Any]] = field(default_factory=list)
    error:    str | None = None

    def to_context_string(self, max_items: int = 5) -> str:
        if not self.success or not self.results:
            return f"[{self.tool}] No results found for: {self.query}"

        lines = [f"[{self.tool}] Results for: {self.query}\n"]
        for i, r in enumerate(self.results[:max_items], 1):
            title   = r.get("title",   "—")
            url     = r.get("url",     "")
            snippet = r.get("snippet", r.get("content", ""))[:400]
            lines.append(f"{i}. {title}\n   {url}\n   {snippet}\n")
        return "\n".join(lines)


class BaseTool(ABC):
    name: str = "base_tool"

    @abstractmethod
    def run(self, query: str, **kwargs) -> ToolResult:
        ...

    def __call__(self, query: str, **kwargs) -> ToolResult:
        return self.run(query, **kwargs)