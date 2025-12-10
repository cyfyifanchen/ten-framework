"""
Constants for Gradium ASR extension.
"""

from ten_ai_base.const import LOG_CATEGORY_KEY_POINT


EXTENSION_NAME = "gradium_asr_python"
"""Name of the Gradium ASR extension."""

PROPERTY_FILE_NAME = "property.json"
"""Name of the property configuration file."""

CMD_PROPERTY_NAME = "cmd"
"""Command property name."""

CMD_IN_FLUSH = "flush"
"""Command to flush the ASR buffer."""

# WebSocket message types
WS_MSG_TYPE_SETUP = "setup"
"""WebSocket message type for initial setup."""

WS_MSG_TYPE_READY = "ready"
"""WebSocket message type for ready confirmation."""

WS_MSG_TYPE_AUDIO = "audio"
"""WebSocket message type for audio data."""

WS_MSG_TYPE_TEXT = "text"
"""WebSocket message type for transcription results."""

WS_MSG_TYPE_VAD = "vad"
"""WebSocket message type for voice activity detection."""

WS_MSG_TYPE_END = "end_of_stream"
"""WebSocket message type for end of stream."""

# Audio configuration
GRADIUM_SAMPLE_RATE = 24000
"""Expected sample rate for Gradium ASR (24kHz)."""

GRADIUM_CHANNELS = 1
"""Expected number of audio channels (mono)."""

GRADIUM_BITS_PER_SAMPLE = 16
"""Expected bits per sample (16-bit PCM)."""

GRADIUM_FRAME_SIZE = 1920
"""Recommended frame size in samples (80ms at 24kHz)."""
