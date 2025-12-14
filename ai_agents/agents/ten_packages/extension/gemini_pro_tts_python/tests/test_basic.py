"""
Basic functionality tests for Gemini Pro TTS extension
"""


def test_import():
    """Test that extension can be imported"""
    from gemini_pro_tts_python.extension import GeminiProTTSExtension

    assert GeminiProTTSExtension is not None


def test_config():
    """Test configuration model"""
    from gemini_pro_tts_python.config import GeminiProTTSConfig

    config = GeminiProTTSConfig(
        params={
            "api_key": "test_key",
            "model": "gemini-2.5-pro-preview-tts",
            "voice": "Charon",
        }
    )

    assert config.params["api_key"] == "test_key"
    assert config.params["model"] == "gemini-2.5-pro-preview-tts"
    assert config.params["voice"] == "Charon"
