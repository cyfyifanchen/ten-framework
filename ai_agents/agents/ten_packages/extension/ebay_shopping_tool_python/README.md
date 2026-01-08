# eBay Shopping Tool Extension

A TEN Framework extension that enables real-time voice shopping assistants to search eBay, get product details, and open items in the browser.

## Features

- **search_ebay** - Search for products on eBay with filters (category, price, condition)
- **open_ebay_item** - Open eBay items or search results in the user's browser
- **get_ebay_item_details** - Get detailed information about specific items

## Quick Start

### 1. Set Environment Variables

```bash
# Required for Agora RTC
export AGORA_APP_ID=your_agora_app_id
export AGORA_APP_CERTIFICATE=your_agora_certificate

# Required for ASR
export DEEPGRAM_API_KEY=your_deepgram_key

# Required for LLM
export OPENAI_API_KEY=your_openai_key
export OPENAI_MODEL=gpt-4o

# Required for TTS
export ELEVENLABS_TTS_KEY=your_elevenlabs_key

# Optional - eBay API (works in demo mode without this)
export EBAY_API_KEY=your_ebay_oauth_token
```

### 2. Get eBay API Credentials (Optional)

1. Go to [eBay Developer Program](https://developer.ebay.com/)
2. Create an application
3. Generate an OAuth token for the Browse API
4. Set the `EBAY_API_KEY` environment variable

Without an API key, the extension works in demo mode with mock data.

### 3. Add to Your Graph

Add the extension to your `property.json`:

```json
{
  "type": "extension",
  "name": "ebay_shopping_tool",
  "addon": "ebay_shopping_tool_python",
  "extension_group": "default",
  "property": {
    "api_key": "${env:EBAY_API_KEY|}",
    "marketplace_id": "EBAY_US",
    "max_results": 5
  }
}
```

Connect it to main_control:

```json
{
  "extension": "main_control",
  "cmd": [
    {
      "names": ["tool_register"],
      "source": [{"extension": "ebay_shopping_tool"}]
    }
  ]
},
{
  "extension": "ebay_shopping_tool",
  "cmd": [
    {
      "name": "tool_call",
      "source": [{"extension": "main_control"}]
    }
  ]
}
```

## Usage Examples

Once the voice assistant is running, you can say:

- "Search for iPhone 15 on eBay"
- "Find me a gaming laptop under 1000 dollars"
- "Open the first result"
- "Tell me more about item number 2"
- "Open the search results in my browser"

## Configuration

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `api_key` | string | "" | eBay Browse API OAuth token |
| `marketplace_id` | string | "EBAY_US" | eBay marketplace (EBAY_US, EBAY_UK, etc.) |
| `max_results` | number | 5 | Maximum search results to return |

## API Reference

### Tools

#### search_ebay

Search for products on eBay.

**Parameters:**
- `query` (string, required) - Search query
- `category` (string, optional) - Category filter
- `max_price` (number, optional) - Maximum price in USD
- `condition` (string, optional) - "new", "used", or "any"

#### open_ebay_item

Open eBay in the browser.

**Parameters:**
- `item_id` (string, optional) - Specific item ID to open
- `search_query` (string, optional) - Open search results page
- `result_index` (number, optional) - Open item from last search (1-based)

#### get_ebay_item_details

Get detailed item information.

**Parameters:**
- `item_id` (string, optional) - Item ID to get details for
- `result_index` (number, optional) - Get details from last search (1-based)

## Architecture

```
Voice Input → [Deepgram ASR] → Text
                                 ↓
                         [OpenAI LLM + Tools]
                                 ↓
                    ┌────────────┴────────────┐
                    ↓                         ↓
            [eBay Tool]              [Text Response]
                    ↓                         ↓
            ┌───────┴───────┐         [ElevenLabs TTS]
            ↓               ↓                 ↓
    [Search API]    [Open Browser]    Voice Output
```

## License

Copyright (c) 2024 Agora IO. All rights reserved.
