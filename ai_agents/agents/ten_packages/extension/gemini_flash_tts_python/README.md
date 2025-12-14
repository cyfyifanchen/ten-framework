# gemini_flash_tts_python

A Google Gemini 2.5 Flash TTS extension for the TEN framework, providing low-latency text-to-speech synthesis.

## Features

- Integration with Google Gemini 2.5 Flash TTS (optimized for low latency)
- Full compatibility with the TEN TTS interface
- 30 prebuilt voices with distinct characteristics
- 24 language support
- Style prompts for tone control
- PCM 16-bit 24kHz mono audio output

## API

Refer to the `api` definition in [manifest.json](manifest.json) and default values in [property.json](property.json).

| **Property** | **Type** | **Description** |
|---|---|---|
| `api_key` | `string` | API key for authenticating with Google Gemini |
| `model` | `string` | Model identifier (default: `gemini-2.5-flash-preview-tts`) |
| `voice` | `string` | Voice name (e.g., `Kore`, `Puck`, `Charon`) |
| `language_code` | `string` | Language code in BCP-47 format (e.g., `en-US`) |
| `style_prompt` | `string` | Style instructions for delivery (e.g., "cheerful and optimistic") |

## Configuration

Set the `GEMINI_API_KEY` environment variable with your Google Gemini API key:

```bash
export GEMINI_API_KEY=your_api_key
```

## Available Voices

30 prebuilt voices including:
- **Kore** - Bright, upbeat
- **Puck** - Smooth, conversational
- **Charon** - Deep, authoritative
- **Fenrir** - Warm, friendly
- **Enceladus** - Clear, professional
- And 25+ more...

## Supported Languages

24 languages including:
- English (US, India)
- Spanish
- French
- German
- Japanese
- Korean
- Hindi
- Portuguese
- And more...

## Usage Example

```json
{
  "params": {
    "api_key": "your-gemini-api-key",
    "model": "gemini-2.5-flash-preview-tts",
    "voice": "Kore",
    "language_code": "en-US",
    "style_prompt": "cheerful and enthusiastic"
  }
}
```

## Differences from Gemini Pro TTS

| Feature | Flash TTS | Pro TTS |
|---------|-----------|---------|
| **Optimization** | Low latency | High quality |
| **Speed** | Faster | Slower |
| **Use Cases** | Real-time, interactive | Podcasts, audiobooks |
| **Cost** | More cost-efficient | Higher quality |

## Audio Specifications

- **Format**: PCM 16-bit
- **Sample Rate**: 24,000 Hz
- **Channels**: Mono (1)
- **Encoding**: Base64 (in API response)

## Code Style & Linting Rules

This extension follows the TEN framework's strict code quality standards. All code must comply with the following rules before being merged:

### Line Length
- **Maximum line length**: 80 characters
- Tools: Black formatter, Pylint

### Type Hints
- **Required for**: All function parameters and return types
- **Preferred**: Use `Optional[T]` instead of `T | None`

### Naming Conventions
- **Classes**: PascalCase
- **Functions/Methods**: snake_case
- **Variables**: snake_case
- **Constants**: UPPER_CASE

### Pre-commit Checklist
Before pushing your code:
- [ ] All lines are ≤ 80 characters
- [ ] Run `task format` (from ai_agents directory)
- [ ] Run `task check` (format check)
- [ ] Run `task lint-extension EXTENSION=gemini_flash_tts_python`
- [ ] All type hints are present
- [ ] Naming conventions followed
- [ ] Exception handling with proper logging
