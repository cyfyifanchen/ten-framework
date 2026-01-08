#
# eBay Shopping Tool Extension for TEN Framework
# Real-time voice shopping assistant that searches eBay and opens browser
# Copyright (c) 2024 Agora IO. All rights reserved.
#
import json
import webbrowser
import aiohttp
from typing import Any, List
from urllib.parse import quote_plus

from ten_runtime import Cmd
from ten_runtime.async_ten_env import AsyncTenEnv
from ten_ai_base.config import BaseConfig
from ten_ai_base.types import (
    LLMToolMetadata,
    LLMToolMetadataParameter,
    LLMToolResult,
)
from ten_ai_base.llm_tool import AsyncLLMToolBaseExtension


# Tool names
TOOL_SEARCH_EBAY = "search_ebay"
TOOL_OPEN_BROWSER = "open_ebay_item"
TOOL_GET_ITEM_DETAILS = "get_ebay_item_details"

# eBay Browse API endpoint (you can also use Finding API)
EBAY_BROWSE_API_ENDPOINT = "https://api.ebay.com/buy/browse/v1/item_summary/search"
EBAY_ITEM_URL_TEMPLATE = "https://www.ebay.com/itm/{item_id}"
EBAY_SEARCH_URL_TEMPLATE = "https://www.ebay.com/sch/i.html?_nkw={query}"


class EbayShoppingToolConfig(BaseConfig):
    # eBay API credentials
    api_key: str = ""  # OAuth token for eBay API
    marketplace_id: str = "EBAY_US"  # Default marketplace
    max_results: int = 5  # Default number of results to return


class EbayShoppingToolExtension(AsyncLLMToolBaseExtension):
    """
    eBay Shopping Tool Extension for TEN Framework.

    This extension provides three tools:
    1. search_ebay - Search for products on eBay
    2. open_ebay_item - Open an eBay item or search results in browser
    3. get_ebay_item_details - Get detailed information about a specific item

    Usage in voice assistant:
    - User: "帮我在eBay上搜索iPhone 15"
    - User: "打开第一个商品"
    - User: "这个商品多少钱？"
    """

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.session = None
        self.config = None
        self.last_search_results = []  # Cache last search results for reference

    async def on_init(self, ten_env: AsyncTenEnv) -> None:
        ten_env.log_debug("EbayShoppingToolExtension on_init")
        self.session = aiohttp.ClientSession()
        await super().on_init(ten_env)

    async def on_start(self, ten_env: AsyncTenEnv) -> None:
        ten_env.log_debug("EbayShoppingToolExtension on_start")
        await super().on_start(ten_env)

        self.config = await EbayShoppingToolConfig.create_async(ten_env=ten_env)

        if not self.config.api_key:
            ten_env.log_warn(
                "eBay API key is missing. Search will use web scraping fallback or return mock data."
            )

    async def on_stop(self, ten_env: AsyncTenEnv) -> None:
        ten_env.log_debug("EbayShoppingToolExtension on_stop")

        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None

    async def on_cmd(self, ten_env: AsyncTenEnv, cmd: Cmd) -> None:
        cmd_name = cmd.get_name()
        ten_env.log_debug(f"EbayShoppingToolExtension on_cmd: {cmd_name}")
        await super().on_cmd(ten_env, cmd)

    def get_tool_metadata(self, ten_env: AsyncTenEnv) -> list[LLMToolMetadata]:
        """Register available tools with the LLM."""
        return [
            LLMToolMetadata(
                name=TOOL_SEARCH_EBAY,
                description="Search for products on eBay. Use this when the user wants to find items to buy, compare prices, or browse products.",
                parameters=[
                    LLMToolMetadataParameter(
                        name="query",
                        type="string",
                        description="The search query for eBay products (e.g., 'iPhone 15 Pro', 'gaming laptop', 'vintage watch')",
                        required=True,
                    ),
                    LLMToolMetadataParameter(
                        name="category",
                        type="string",
                        description="Optional category to filter results (e.g., 'Electronics', 'Clothing', 'Home')",
                        required=False,
                    ),
                    LLMToolMetadataParameter(
                        name="max_price",
                        type="number",
                        description="Optional maximum price filter in USD",
                        required=False,
                    ),
                    LLMToolMetadataParameter(
                        name="condition",
                        type="string",
                        description="Item condition: 'new', 'used', or 'any'",
                        required=False,
                    ),
                ],
            ),
            LLMToolMetadata(
                name=TOOL_OPEN_BROWSER,
                description="Open an eBay item page or search results in the user's web browser. Use this when the user wants to view, buy, or see more details about a product.",
                parameters=[
                    LLMToolMetadataParameter(
                        name="item_id",
                        type="string",
                        description="The eBay item ID to open. If not provided, opens the search results page.",
                        required=False,
                    ),
                    LLMToolMetadataParameter(
                        name="search_query",
                        type="string",
                        description="Search query to open in browser (used if item_id is not provided)",
                        required=False,
                    ),
                    LLMToolMetadataParameter(
                        name="result_index",
                        type="number",
                        description="Index of the search result to open (1-based, e.g., 1 for first result)",
                        required=False,
                    ),
                ],
            ),
            LLMToolMetadata(
                name=TOOL_GET_ITEM_DETAILS,
                description="Get detailed information about a specific eBay item including price, seller info, shipping, and condition.",
                parameters=[
                    LLMToolMetadataParameter(
                        name="item_id",
                        type="string",
                        description="The eBay item ID to get details for",
                        required=False,
                    ),
                    LLMToolMetadataParameter(
                        name="result_index",
                        type="number",
                        description="Index of the search result to get details for (1-based)",
                        required=False,
                    ),
                ],
            ),
        ]

    async def run_tool(
        self, ten_env: AsyncTenEnv, name: str, args: dict
    ) -> LLMToolResult | None:
        """Execute the requested tool."""
        ten_env.log_info(f"Running tool: {name} with args: {args}")

        try:
            if name == TOOL_SEARCH_EBAY:
                result = await self._search_ebay(ten_env, args)
                return {"content": json.dumps(result, ensure_ascii=False)}

            elif name == TOOL_OPEN_BROWSER:
                result = await self._open_browser(ten_env, args)
                return {"content": json.dumps(result, ensure_ascii=False)}

            elif name == TOOL_GET_ITEM_DETAILS:
                result = await self._get_item_details(ten_env, args)
                return {"content": json.dumps(result, ensure_ascii=False)}

            else:
                return {"content": json.dumps({"error": f"Unknown tool: {name}"})}

        except Exception as e:
            ten_env.log_error(f"Tool execution error: {str(e)}")
            return {"content": json.dumps({"error": str(e)})}

    async def _search_ebay(self, ten_env: AsyncTenEnv, args: dict) -> dict:
        """Search eBay for products."""
        query = args.get("query", "")
        if not query:
            return {"error": "Search query is required"}

        category = args.get("category")
        max_price = args.get("max_price")
        condition = args.get("condition", "any")

        ten_env.log_info(f"Searching eBay for: {query}")

        # If API key is available, use eBay Browse API
        if self.config.api_key:
            results = await self._search_via_api(
                ten_env, query, category, max_price, condition
            )
        else:
            # Fallback: return mock data for demo or use alternative approach
            results = self._get_mock_search_results(query)

        # Cache results for later reference
        self.last_search_results = results.get("items", [])

        return results

    async def _search_via_api(
        self,
        ten_env: AsyncTenEnv,
        query: str,
        category: str = None,
        max_price: float = None,
        condition: str = "any",
    ) -> dict:
        """Search using eBay Browse API."""
        await self._ensure_session(ten_env)

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "X-EBAY-C-MARKETPLACE-ID": self.config.marketplace_id,
            "Content-Type": "application/json",
        }

        params = {
            "q": query,
            "limit": self.config.max_results,
        }

        # Add filters
        filters = []
        if max_price:
            filters.append(f"price:[..{max_price}]")
        if condition and condition != "any":
            condition_map = {"new": "NEW", "used": "USED"}
            if condition.lower() in condition_map:
                filters.append(f"conditions:{{{condition_map[condition.lower()]}}}")

        if filters:
            params["filter"] = ",".join(filters)

        try:
            async with self.session.get(
                EBAY_BROWSE_API_ENDPOINT, headers=headers, params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_api_response(data, query)
                else:
                    error_text = await response.text()
                    ten_env.log_error(f"eBay API error: {response.status} - {error_text}")
                    return self._get_mock_search_results(query)

        except Exception as e:
            ten_env.log_error(f"eBay API request failed: {str(e)}")
            return self._get_mock_search_results(query)

    def _parse_api_response(self, data: dict, query: str) -> dict:
        """Parse eBay API response into a structured format."""
        items = []
        for item in data.get("itemSummaries", []):
            items.append({
                "id": item.get("itemId", ""),
                "title": item.get("title", ""),
                "price": item.get("price", {}).get("value", "N/A"),
                "currency": item.get("price", {}).get("currency", "USD"),
                "condition": item.get("condition", "Unknown"),
                "image_url": item.get("image", {}).get("imageUrl", ""),
                "item_url": item.get("itemWebUrl", ""),
                "seller": item.get("seller", {}).get("username", "Unknown"),
                "shipping": item.get("shippingOptions", [{}])[0].get(
                    "shippingCost", {}
                ).get("value", "See listing"),
            })

        return {
            "query": query,
            "total_results": data.get("total", len(items)),
            "items": items,
            "message": f"Found {len(items)} items for '{query}'"
        }

    def _get_mock_search_results(self, query: str) -> dict:
        """Return mock search results for demo purposes."""
        # This is used when API key is not available
        mock_items = [
            {
                "id": "123456789001",
                "title": f"{query} - Premium Quality Item 1",
                "price": "299.99",
                "currency": "USD",
                "condition": "New",
                "image_url": "",
                "item_url": f"https://www.ebay.com/itm/123456789001",
                "seller": "top_seller_2024",
                "shipping": "Free",
            },
            {
                "id": "123456789002",
                "title": f"{query} - Great Deal Item 2",
                "price": "199.99",
                "currency": "USD",
                "condition": "Used - Like New",
                "image_url": "",
                "item_url": f"https://www.ebay.com/itm/123456789002",
                "seller": "bargain_hunter",
                "shipping": "9.99",
            },
            {
                "id": "123456789003",
                "title": f"{query} - Budget Option Item 3",
                "price": "149.99",
                "currency": "USD",
                "condition": "New",
                "image_url": "",
                "item_url": f"https://www.ebay.com/itm/123456789003",
                "seller": "value_store",
                "shipping": "Free",
            },
        ]

        return {
            "query": query,
            "total_results": len(mock_items),
            "items": mock_items,
            "message": f"Found {len(mock_items)} items for '{query}' (demo mode - set EBAY_API_KEY for real results)",
            "demo_mode": True,
        }

    async def _open_browser(self, ten_env: AsyncTenEnv, args: dict) -> dict:
        """Open eBay in the user's browser."""
        item_id = args.get("item_id")
        search_query = args.get("search_query")
        result_index = args.get("result_index")

        # If result_index is provided, get item from cached results
        if result_index and self.last_search_results:
            idx = int(result_index) - 1  # Convert to 0-based index
            if 0 <= idx < len(self.last_search_results):
                item = self.last_search_results[idx]
                item_id = item.get("id")
                url = item.get("item_url") or EBAY_ITEM_URL_TEMPLATE.format(item_id=item_id)

                ten_env.log_info(f"Opening browser for item #{result_index}: {url}")
                webbrowser.open(url)

                return {
                    "success": True,
                    "action": "opened_item",
                    "item_title": item.get("title", ""),
                    "url": url,
                    "message": f"Opened '{item.get('title', 'item')}' in your browser"
                }
            else:
                return {
                    "success": False,
                    "error": f"Invalid result index. Available: 1-{len(self.last_search_results)}"
                }

        # Open specific item by ID
        if item_id:
            url = EBAY_ITEM_URL_TEMPLATE.format(item_id=item_id)
            ten_env.log_info(f"Opening browser for item: {url}")
            webbrowser.open(url)
            return {
                "success": True,
                "action": "opened_item",
                "item_id": item_id,
                "url": url,
                "message": f"Opened eBay item {item_id} in your browser"
            }

        # Open search results page
        if search_query:
            encoded_query = quote_plus(search_query)
            url = EBAY_SEARCH_URL_TEMPLATE.format(query=encoded_query)
            ten_env.log_info(f"Opening browser for search: {url}")
            webbrowser.open(url)
            return {
                "success": True,
                "action": "opened_search",
                "query": search_query,
                "url": url,
                "message": f"Opened eBay search for '{search_query}' in your browser"
            }

        return {
            "success": False,
            "error": "Please provide item_id, search_query, or result_index"
        }

    async def _get_item_details(self, ten_env: AsyncTenEnv, args: dict) -> dict:
        """Get detailed information about an eBay item."""
        item_id = args.get("item_id")
        result_index = args.get("result_index")

        # If result_index is provided, get item from cached results
        if result_index and self.last_search_results:
            idx = int(result_index) - 1
            if 0 <= idx < len(self.last_search_results):
                item = self.last_search_results[idx]
                return {
                    "success": True,
                    "item": item,
                    "message": f"Details for item #{result_index}: {item.get('title', '')}"
                }
            else:
                return {
                    "success": False,
                    "error": f"Invalid result index. Available: 1-{len(self.last_search_results)}"
                }

        if not item_id:
            return {"success": False, "error": "Please provide item_id or result_index"}

        # For API-based detail fetching (requires eBay API)
        if self.config.api_key:
            return await self._get_item_details_via_api(ten_env, item_id)

        # Fallback for demo mode
        return {
            "success": True,
            "item": {
                "id": item_id,
                "title": "Item details not available in demo mode",
                "message": "Set EBAY_API_KEY environment variable for full item details"
            },
            "demo_mode": True
        }

    async def _get_item_details_via_api(self, ten_env: AsyncTenEnv, item_id: str) -> dict:
        """Get item details using eBay API."""
        await self._ensure_session(ten_env)

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "X-EBAY-C-MARKETPLACE-ID": self.config.marketplace_id,
        }

        url = f"https://api.ebay.com/buy/browse/v1/item/{item_id}"

        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "success": True,
                        "item": {
                            "id": data.get("itemId", item_id),
                            "title": data.get("title", ""),
                            "price": data.get("price", {}).get("value", "N/A"),
                            "currency": data.get("price", {}).get("currency", "USD"),
                            "condition": data.get("condition", "Unknown"),
                            "description": data.get("shortDescription", ""),
                            "seller": data.get("seller", {}).get("username", "Unknown"),
                            "seller_rating": data.get("seller", {}).get("feedbackPercentage", "N/A"),
                            "location": data.get("itemLocation", {}).get("city", "Unknown"),
                            "shipping": data.get("shippingOptions", [{}])[0].get(
                                "shippingCost", {}
                            ).get("value", "See listing"),
                            "returns_accepted": data.get("returnTerms", {}).get("returnsAccepted", False),
                            "item_url": data.get("itemWebUrl", ""),
                        }
                    }
                else:
                    return {"success": False, "error": f"API error: {response.status}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _ensure_session(self, ten_env: AsyncTenEnv):
        """Ensure aiohttp session is initialized."""
        if self.session is None or self.session.closed:
            ten_env.log_debug("Initializing new aiohttp session")
            self.session = aiohttp.ClientSession()
