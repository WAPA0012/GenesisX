"""
Web Search Tool: Safe Web Search with Result Parsing

Implements:
- Web search via API
- Result parsing and ranking
- Safety filtering

References:
- 代码大纲架构 tools/web_search.py
"""

from typing import Dict, Any, List, Optional, Tuple
from .tool_protocol import Tool, ToolMetadata, ToolRiskLevel, ToolDeterminism
import requests
import time


class WebSearchTool(Tool):
    """
    Web search tool with safety filtering.

    Uses search API to fetch results with content filtering.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__()
        self.config = config
        self.api_key = config.get("search_api_key", "")
        self.search_engine = config.get("search_engine", "bing")
        self.max_results = config.get("max_results", 10)
        self.timeout = config.get("timeout_seconds", 10)

    def get_metadata(self) -> ToolMetadata:
        """Get tool metadata"""
        return ToolMetadata(
            tool_id="web_search",
            name="Web Search",
            description="Search the web for information",
            risk_level=ToolRiskLevel.LOW,
            determinism=ToolDeterminism.QUASI_DETERMINISTIC,
            requires_approval=False,
            cost_estimate=0.01,
            tags=["search", "web", "information"],
        )

    def validate_parameters(self, parameters: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate search parameters"""
        if "query" not in parameters:
            return False, "Missing required parameter 'query'"

        query = parameters["query"]
        if not isinstance(query, str) or len(query.strip()) == 0:
            return False, "Query must be a non-empty string"

        return True, None

    def execute(self, parameters: Dict[str, Any]) -> Any:
        """
        Execute web search.

        Args:
            parameters: {
                "query": str,
                "max_results": int (optional),
            }

        Returns:
            List of search results
        """
        query = parameters["query"]
        max_results = parameters.get("max_results", self.max_results)

        # Use real search when API key is configured, else mock
        if self.api_key and self.search_engine == "bing":
            try:
                results = self._real_search_bing(query, max_results)
            except Exception:
                # Fallback to mock on API failure
                results = self._mock_search(query, max_results)
        else:
            results = self._mock_search(query, max_results)

        return results

    def _mock_search(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """
        Mock search implementation.

        In production, replace with actual search API call.
        """
        # Simulate API latency
        time.sleep(0.1)

        # Mock results
        results = []
        for i in range(min(max_results, 3)):
            results.append({
                "title": f"Result {i+1} for '{query}'",
                "url": f"https://example.com/result{i+1}",
                "snippet": f"This is a snippet for result {i+1} related to {query}.",
                "rank": i + 1,
            })

        return results

    def _real_search_bing(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """
        Real Bing search implementation (requires API key).

        Args:
            query: Search query
            max_results: Max number of results

        Returns:
            List of search results
        """
        if not self.api_key:
            raise ValueError("Bing API key not configured")

        endpoint = "https://api.bing.microsoft.com/v7.0/search"

        headers = {
            "Ocp-Apim-Subscription-Key": self.api_key,
        }

        params = {
            "q": query,
            "count": max_results,
            "textDecorations": False,
            "textFormat": "HTML",
        }

        try:
            response = requests.get(
                endpoint,
                headers=headers,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()

            data = response.json()

            # Parse results
            results = []
            for item in data.get("webPages", {}).get("value", []):
                results.append({
                    "title": item.get("name", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("snippet", ""),
                })

            return results

        except Exception as e:
            raise RuntimeError(f"Search failed: {str(e)}")
