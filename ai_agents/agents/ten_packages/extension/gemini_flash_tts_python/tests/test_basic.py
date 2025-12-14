"""
Basic functionality tests for Gemini Flash TTS extension
"""


def test_import():
    """Test that extension can be imported"""
    from gemini_flash_tts_python.extension import (
        GeminiFlashTTSExtension,
    )

    assert GeminiFlashTTSExtension is not None


def test_config():
    """Test configuration model"""
    from gemini_flash_tts_python.config import GeminiFlashTTSConfig

    config = GeminiFlashTTSConfig(
        params={
            "api_key": "test_key",
            "model": "gemini-2.5-flash-preview-tts",
            "voice": "Kore",
        }
    )

    assert config.params["api_key"] == "test_key"
    assert config.params["model"] == "gemini-2.5-flash-preview-tts"
    assert config.params["voice"] == "Kore"
