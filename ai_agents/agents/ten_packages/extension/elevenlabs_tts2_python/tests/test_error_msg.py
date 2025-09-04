import sys
from pathlib import Path

# Add project root to sys.path to allow running tests from this directory
project_root = str(Path(__file__).resolve().parents[6])
if project_root not in sys.path:
    sys.path.insert(0, project_root)

#
# Copyright © 2024 Agora
# This file is part of TEN Framework, an open source project.
# Licensed under the Apache License, Version 2.0, with certain conditions.
# Refer to the "LICENSE" file in the root directory for more information.
#
import json
from typing import Any
from unittest.mock import patch, AsyncMock
import tempfile
import os
import asyncio
import filecmp
import shutil
import threading

from ten_runtime import (
    ExtensionTester,
    TenEnvTester,
    Cmd,
    CmdResult,
    StatusCode,
    Data,
)
from ten_ai_base.struct import TTSTextInput, TTSFlush
from ten_ai_base.message import ModuleVendorException, ModuleErrorVendorInfo


# ================ test empty params ================
class ExtensionTesterEmptyParams(ExtensionTester):
    def __init__(self):
        super().__init__()
        self.error_received = False
        self.error_code = None
        self.error_message = None

    def on_start(self, ten_env_tester: TenEnvTester) -> None:
        """Called when test starts"""
        ten_env_tester.log_info("Test started")
        ten_env_tester.on_start_done()

    def on_data(self, ten_env: TenEnvTester, data) -> None:
        name = data.get_name()
        ten_env.log_info(f"on_data name: {name}")

        if name == "error":
            self.error_received = True
            json_str, _ = data.get_property_to_json(None)
            error_data = json.loads(json_str)

            self.error_code = error_data.get("code")
            self.error_message = error_data.get("message", "")

            ten_env.log_info(
                f"Received error: code={self.error_code}, message={self.error_message}"
            )
            ten_env.stop_test()


def test_empty_params_fatal_error():
    """Test that empty params raises FATAL ERROR with code -1000"""
    print("Starting test_empty_params_fatal_error...")

    # Empty params configuration
    empty_params_config = {"params": {"key": "", "voice_id": ""}}

    tester = ExtensionTesterEmptyParams()
    tester.set_test_mode_single(
        "elevenlabs_tts2_python", json.dumps(empty_params_config)
    )

    print("Running test...")
    tester.run()
    print("Test completed.")

    # Verify FATAL ERROR was received
    assert tester.error_received, "Expected to receive error message"
    assert (
        tester.error_code == -1000
    ), f"Expected error code -1000 (FATAL_ERROR), got {tester.error_code}"
    assert tester.error_message is not None, "Error message should not be None"
    assert len(tester.error_message) > 0, "Error message should not be empty"

    print(
        f"✅ Empty params test passed: code={tester.error_code}, message={tester.error_message}"
    )
    print("Test verification completed successfully.")


# ================ test invalid params ================
class ExtensionTesterInvalidParams(ExtensionTester):
    def __init__(self):
        super().__init__()
        self.error_received = False
        self.error_code = None
        self.error_message = None
        self.error_module = None
        self.vendor_info = None

    def on_start(self, ten_env_tester: TenEnvTester) -> None:
        """Called when test starts, sends a TTS request to trigger the logic."""
        ten_env_tester.log_info(
            "Test started, sending TTS request to trigger mocked error"
        )

        tts_input = TTSTextInput(
            request_id="test-request-for-invalid-params",
            text="This text will trigger the mocked error.",
        )
        data = Data.create("tts_text_input")
        data.set_property_from_json(None, tts_input.model_dump_json())
        ten_env_tester.send_data(data)

        ten_env_tester.on_start_done()

    def on_data(self, ten_env: TenEnvTester, data) -> None:
        name = data.get_name()
        ten_env.log_info(f"on_data name: {name}")

        if name == "error":
            self.error_received = True
            json_str, _ = data.get_property_to_json(None)
            error_data = json.loads(json_str)

            self.error_code = error_data.get("code")
            self.error_message = error_data.get("message", "")
            self.error_module = error_data.get("module", "")
            self.vendor_info = error_data.get("vendor_info", {})

            ten_env.log_info(
                f"Received error: code={self.error_code}, message={self.error_message}, module={self.error_module}"
            )
            ten_env.log_info(f"Vendor info: {self.vendor_info}")

            ten_env.stop_test()


@patch("elevenlabs_tts2_python.extension.ElevenLabsTTS2Client")
def test_invalid_params_fatal_error(MockElevenLabsTTS2Client):
    """Test that an error from the TTS client is handled correctly with a mock."""

    print("Starting test_invalid_params_fatal_error with mock...")

    # --- Mock Configuration ---
    mock_instance = MockElevenLabsTTS2Client.return_value
    mock_instance.close = AsyncMock()
    mock_instance.cancel = AsyncMock()

    # Mock the synthesizer
    mock_synthesizer = AsyncMock()
    mock_instance.synthesizer = mock_synthesizer
    mock_synthesizer.send_text_in_connection = False
    mock_synthesizer.websocket_task = None

    # Mock send_text to raise an exception
    async def mock_send_text_with_error(text_data):
        vendor_info = ModuleErrorVendorInfo(
            vendor="elevenlabs",
            code="40000",
            message="Invalid voice or parameters",
        )
        raise ModuleVendorException(vendor_info)

    mock_instance.send_text.side_effect = mock_send_text_with_error

    # Mock the client constructor to properly handle the response_msgs queue
    def mock_client_init(
        config,
        ten_env,
        error_callback=None,
        response_msgs=None,
        ttfb_metrics_callback=None,
    ):
        # Store the real queue passed by the extension
        mock_instance.response_msgs = response_msgs
        return mock_instance

    MockElevenLabsTTS2Client.side_effect = mock_client_init

    # --- Test Setup ---
    # Config with valid key and voice_id so on_init passes
    invalid_params_config = {
        "key": "valid_key_for_test",
        "voice_id": "valid_voice_id_for_test",
        "params": {"voice_id": "invalid_voice_id"},
    }

    tester = ExtensionTesterInvalidParams()
    tester.set_test_mode_single(
        "elevenlabs_tts2_python", json.dumps(invalid_params_config)
    )

    print("Running test with mock...")
    tester.run()
    print("Test with mock completed.")

    # --- Assertions ---
    assert tester.error_received, "Expected to receive error message"
    assert (
        tester.error_code == 1000
    ), f"Expected error code 1000, got {tester.error_code}"
    assert tester.error_message is not None, "Error message should not be None"
    assert len(tester.error_message) > 0, "Error message should not be empty"

    # Verify vendor_info
    vendor_info = tester.vendor_info
    assert vendor_info is not None, "Expected vendor_info to be present"
    assert (
        vendor_info.get("vendor") == "elevenlabs"
    ), f"Expected vendor 'elevenlabs', got {vendor_info.get('vendor')}"
    assert "code" in vendor_info, "Expected 'code' in vendor_info"
    assert "message" in vendor_info, "Expected 'message' in vendor_info"

    print(
        f"✅ Invalid params test passed with mock: code={tester.error_code}, message={tester.error_message}"
    )
    print(f"✅ Vendor info: {tester.vendor_info}")
    print("Test verification completed successfully.")
