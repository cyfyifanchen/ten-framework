# Shopping Assistant Example

A real-time voice-powered shopping assistant that searches eBay and opens products in your browser.

## Overview

This example demonstrates how to build a voice shopping assistant using TEN Framework:

- **Real-time voice interaction** - Talk to your assistant naturally
- **eBay integration** - Search products, get details, compare prices
- **Browser automation** - Automatically open items in your browser

## Quick Start

### Prerequisites

```bash
# Clone and setup
cd ai_agents/agents/examples/shopping-assistant

# Set environment variables
export AGORA_APP_ID=your_agora_app_id
export DEEPGRAM_API_KEY=your_deepgram_key
export OPENAI_API_KEY=your_openai_key
export ELEVENLABS_TTS_KEY=your_elevenlabs_key

# Optional: eBay API for real results (demo mode works without this)
export EBAY_API_KEY=your_ebay_oauth_token
```

### Run the Agent

```bash
# From the ai_agents directory
task run -- shopping-assistant
```

### Connect

Use the TEN web client or Agora SDK to connect to the agent.

## Voice Commands

Try saying:

| Command | Action |
|---------|--------|
| "Search for MacBook Pro" | Searches eBay |
| "Find me headphones under 50 dollars" | Searches with price filter |
| "Open the first result" | Opens item in browser |
| "Tell me about item 2" | Gets item details |
| "Show me the search results" | Opens eBay search page |

## Graph Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Agora RTC  │ ──► │ Deepgram    │ ──► │ Main        │
│  (Audio)    │     │ ASR         │     │ Control     │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                    ┌──────────────────────────┼──────────────────────────┐
                    │                          │                          │
                    ▼                          ▼                          ▼
            ┌───────────────┐          ┌───────────────┐          ┌───────────────┐
            │ OpenAI LLM    │          │ eBay Tool     │          │ ElevenLabs    │
            │ (GPT-4o)      │ ◄──────► │ (Shopping)    │          │ TTS           │
            └───────────────┘          └───────────────┘          └───────┬───────┘
                                                                          │
                                                                          ▼
                                                                  ┌───────────────┐
                                                                  │ Agora RTC     │
                                                                  │ (Audio Out)   │
                                                                  └───────────────┘
```

## Customization

### Change Language

Update the LLM prompt in `tenapp/property.json`:

```json
{
  "name": "llm",
  "property": {
    "prompt": "你是一个购物助手，帮助用户在eBay上搜索商品..."
  }
}
```

### Change Marketplace

Update the eBay tool property:

```json
{
  "name": "ebay_shopping_tool",
  "property": {
    "marketplace_id": "EBAY_UK"
  }
}
```

Available marketplaces: `EBAY_US`, `EBAY_UK`, `EBAY_DE`, `EBAY_AU`, etc.

## Files

```
shopping-assistant/
├── README.md           # This file
└── tenapp/
    └── property.json   # Graph configuration
```

## Related

- [eBay Shopping Tool Extension](../../ten_packages/extension/ebay_shopping_tool_python/README.md)
- [Voice Assistant Example](../voice-assistant/README.md)
- [TEN Framework Documentation](https://doc.theten.ai/)
