"""
Gradium ASR extension for TEN framework.
"""

import asyncio
import base64
import json
from typing import Optional
import traceback

import websockets
from websockets.asyncio.client import ClientConnection
from ten import AsyncTenEnv, AudioFrame
from ten_ai_base.asr import (
    AsyncASRBaseExtension,
    ASRBufferConfigModeDiscard,
)
from ten_ai_base.helper import AudioTimeline
from ten_ai_base.log import logger
from ten_ai_base.types import ModuleError, ModuleErrorCode, ModuleErrorVendorInfo
from ten_ai_base.helper import AsyncEventEmitter, AsyncQueue

from .config import GradiumASRConfig
from .const import (
    LOG_CATEGORY_ERROR,
    LOG_CATEGORY_KEY_POINT,
    WS_MSG_TYPE_SETUP,
    WS_MSG_TYPE_READY,
    WS_MSG_TYPE_AUDIO,
    WS_MSG_TYPE_TEXT,
    WS_MSG_TYPE_VAD,
    WS_MSG_TYPE_END,
    GRADIUM_SAMPLE_RATE,
)


class GradiumASRExtension(AsyncASRBaseExtension):
    """Gradium ASR extension implementation."""

    def __init__(self, name: str):
        """
        Initialize the Gradium ASR extension.

        Args:
            name: Extension name.
        """
        super().__init__(name)
        self.config: Optional[GradiumASRConfig] = None
        self.websocket: Optional[ClientConnection] = None
        self.connected = False
        self.audio_timeline = AudioTimeline()
        self.receive_task: Optional[asyncio.Task] = None
        self.audio_queue: AsyncQueue = AsyncQueue()
        self.send_task: Optional[asyncio.Task] = None

    def vendor(self) -> str:
        """Get the ASR vendor name."""
        return "gradium"

    async def on_init(self, ten_env: AsyncTenEnv) -> None:
        """
        Initialize the extension.

        Args:
            ten_env: TEN environment.
        """
        await super().on_init(ten_env)

        # Load configuration
        config_json, _ = await ten_env.get_property_to_json("")

        try:
            self.config = GradiumASRConfig.model_validate_json(config_json)
            self.config.update(self.config.params)
            ten_env.log_info(
                f"config: {self.config.to_json(sensitive_handling=True)}",
                category=LOG_CATEGORY_KEY_POINT,
            )
        except Exception as e:
            ten_env.log_error(
                f"Failed to parse config: {traceback.format_exc()}",
                category=LOG_CATEGORY_ERROR,
            )
            await self.send_asr_error(
                ModuleError(
                    module="asr",
                    code=ModuleErrorCode.FATAL_ERROR.value,
                    message=f"Failed to parse config: {str(e)}",
                )
            )

        ten_env.log_info("Gradium ASR extension initialized")

    async def on_deinit(self, ten_env: AsyncTenEnv) -> None:
        """
        Deinitialize the extension.

        Args:
            ten_env: TEN environment.
        """
        ten_env.log_info("Gradium ASR extension deinitialized")
        await super().on_deinit(ten_env)

    async def start_connection(self) -> None:
        """Start the WebSocket connection to Gradium ASR service."""
        if self.connected:
            logger.info("Already connected to Gradium ASR")
            return

        try:
            logger.info(f"Connecting to Gradium ASR at {self.config.get_websocket_url()}")

            # Connect to WebSocket
            self.websocket = await websockets.connect(
                self.config.get_websocket_url(),
                additional_headers={"x-api-key": self.config.api_key},
            )

            # Send setup message
            setup_message = {
                "type": WS_MSG_TYPE_SETUP,
                "model_name": self.config.model_name,
                "input_format": self.config.input_format,
            }

            if self.config.language:
                setup_message["language"] = self.config.language

            await self.websocket.send(json.dumps(setup_message))
            logger.info(f"Sent setup message: {setup_message}")

            # Wait for ready message
            ready_msg = await self.websocket.recv()
            ready_data = json.loads(ready_msg)

            if ready_data.get("type") == WS_MSG_TYPE_READY:
                logger.info(f"Received ready message: {ready_data}")
                self.connected = True

                # Start receive task
                self.receive_task = asyncio.create_task(self._receive_loop())

                # Start send task
                self.send_task = asyncio.create_task(self._send_loop())

                logger.info("Successfully connected to Gradium ASR")
            else:
                raise Exception(f"Unexpected message type: {ready_data.get('type')}")

        except Exception as e:
            logger.error(f"Failed to connect to Gradium ASR: {traceback.format_exc()}")
            self.connected = False
            await self.send_asr_error(
                ModuleError(
                    module="asr",
                    code=ModuleErrorCode.FATAL_ERROR.value,
                    message=f"Failed to connect: {str(e)}",
                ),
                ModuleErrorVendorInfo(
                    vendor=self.vendor(), code="connection_error", message=str(e)
                ),
            )

    async def stop_connection(self) -> None:
        """Stop the WebSocket connection."""
        if not self.connected:
            return

        try:
            # Send end of stream message
            if self.websocket:
                end_message = {"type": WS_MSG_TYPE_END}
                await self.websocket.send(json.dumps(end_message))
                logger.info("Sent end of stream message")

            # Cancel tasks
            if self.receive_task:
                self.receive_task.cancel()
                try:
                    await self.receive_task
                except asyncio.CancelledError:
                    pass

            if self.send_task:
                self.send_task.cancel()
                try:
                    await self.send_task
                except asyncio.CancelledError:
                    pass

            # Close WebSocket
            if self.websocket:
                await self.websocket.close()
                self.websocket = None

            self.connected = False
            logger.info("Disconnected from Gradium ASR")

        except Exception as e:
            logger.error(f"Error stopping connection: {traceback.format_exc()}")

    async def send_audio(self, frame: AudioFrame, session_id: str | None) -> bool:
        """
        Send audio frame to Gradium ASR service.

        Args:
            frame: Audio frame to send.
            session_id: Session ID (optional).

        Returns:
            True if audio was sent successfully.
        """
        if not self.connected:
            logger.warning("Not connected to Gradium ASR, skipping audio frame")
            return False

        try:
            buf = frame.lock_buf()
            frame_bytes = bytes(buf)
            frame.unlock_buf(buf)

            # Track audio timeline
            self.audio_timeline.add_user_audio(
                int(len(frame_bytes) / (self.config.sample_rate / 1000 * 2))
            )

            # Queue audio for sending
            await self.audio_queue.put(frame_bytes)

            return True

        except Exception as e:
            logger.error(f"Error sending audio: {traceback.format_exc()}")
            return False

    async def _send_loop(self) -> None:
        """Background task to send audio data to WebSocket."""
        try:
            while self.connected:
                # Get audio from queue
                frame_bytes = await self.audio_queue.get()

                if frame_bytes is None:
                    break

                # Encode to base64
                audio_b64 = base64.b64encode(frame_bytes).decode("utf-8")

                # Send audio message
                audio_message = {"type": WS_MSG_TYPE_AUDIO, "audio": audio_b64}
                await self.websocket.send(json.dumps(audio_message))

        except asyncio.CancelledError:
            logger.info("Send loop cancelled")
        except Exception as e:
            logger.error(f"Error in send loop: {traceback.format_exc()}")
            self.connected = False

    async def _receive_loop(self) -> None:
        """Background task to receive messages from WebSocket."""
        try:
            while self.connected and self.websocket:
                message = await self.websocket.recv()
                data = json.loads(message)

                msg_type = data.get("type")

                if msg_type == WS_MSG_TYPE_TEXT:
                    await self._handle_text_message(data)
                elif msg_type == WS_MSG_TYPE_VAD:
                    await self._handle_vad_message(data)
                else:
                    logger.debug(f"Received message: {data}")

        except asyncio.CancelledError:
            logger.info("Receive loop cancelled")
        except Exception as e:
            logger.error(f"Error in receive loop: {traceback.format_exc()}")
            self.connected = False
            await self.send_asr_error(
                ModuleError(
                    module="asr",
                    code=ModuleErrorCode.NON_FATAL_ERROR.value,
                    message=f"Receive error: {str(e)}",
                ),
                ModuleErrorVendorInfo(
                    vendor=self.vendor(), code="receive_error", message=str(e)
                ),
            )

    async def _handle_text_message(self, data: dict) -> None:
        """
        Handle transcription text message.

        Args:
            data: Message data containing transcription.
        """
        try:
            text = data.get("text", "")
            start_ms = int(data.get("start_ms", 0))
            end_ms = int(data.get("end_ms", 0))
            is_final = data.get("final", False)

            duration_ms = end_ms - start_ms

            logger.debug(
                f"Transcription: '{text}' (final={is_final}, start={start_ms}, duration={duration_ms})"
            )

            # Send ASR result
            await self._handle_asr_result(
                text=text,
                final=is_final,
                start_ms=start_ms,
                duration_ms=duration_ms,
                language=self.config.language,
            )

        except Exception as e:
            logger.error(f"Error handling text message: {traceback.format_exc()}")

    async def _handle_vad_message(self, data: dict) -> None:
        """
        Handle voice activity detection message.

        Args:
            data: VAD message data.
        """
        # VAD messages can be used for additional features like
        # detecting when the user has finished speaking
        logger.debug(f"VAD message: {data}")

    async def finalize(self, session_id: str | None) -> None:
        """
        Finalize the current ASR session.

        Args:
            session_id: Session ID (optional).
        """
        logger.info("Finalizing ASR session")
        # Gradium doesn't require explicit finalization per session
        # The end_of_stream message is sent when stopping the connection

    def is_connected(self) -> bool:
        """Check if connected to Gradium ASR service."""
        return self.connected

    def input_audio_sample_rate(self) -> int:
        """Get the input audio sample rate."""
        return self.config.sample_rate if self.config else GRADIUM_SAMPLE_RATE

    def input_audio_channels(self) -> int:
        """Get the number of input audio channels."""
        return self.config.channels if self.config else 1

    def input_audio_sample_width(self) -> int:
        """Get the input audio sample width in bytes."""
        return self.config.bits_per_sample // 8 if self.config else 2

    def buffer_strategy(self):
        """Get the buffer strategy (discard mode for WebSocket)."""
        return ASRBufferConfigModeDiscard()
