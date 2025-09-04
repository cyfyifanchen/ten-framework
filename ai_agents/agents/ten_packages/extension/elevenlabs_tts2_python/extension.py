#
# This file is part of TEN Framework, an open source project.
# Licensed under the Apache License, Version 2.0.
# See the LICENSE file for more information.
#
import asyncio
from datetime import datetime
import os
import traceback
from typing import Tuple

from ten_ai_base.helper import PCMWriter
from ten_ai_base.message import (
    ModuleError,
    ModuleErrorCode,
    ModuleType,
    ModuleVendorException,
    TTSAudioEndReason,
)
from ten_ai_base.struct import TTSTextInput
from ten_ai_base.tts2 import AsyncTTS2BaseExtension
from .elevenlabs_tts import ElevenLabsTTS2Client, ElevenLabsTTS2Config
from ten_runtime import (
    AsyncTenEnv,
    Data,
)


class ElevenLabsTTS2Extension(AsyncTTS2BaseExtension):
    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.config: ElevenLabsTTS2Config = None
        self.client: ElevenLabsTTS2Client = None
        self.current_request_id: str = None
        self.current_turn_id: int = -1
        self.stop_event: asyncio.Event = None
        self.recorder: PCMWriter = None
        self.request_start_ts: datetime | None = None
        self.request_total_audio_duration: int | None = None
        self.response_msgs = asyncio.Queue[Tuple[bytes, bool, str]]()
        self.recorder_map: dict[str, PCMWriter] = (
            {}
        )  # store different request id pcmwriter
        self.last_completed_request_id: str | None = None
        self.completed_request_ids: set[str] = set()
        self.msg_polling_task: asyncio.Task = None
        self.init_complete: asyncio.Event = asyncio.Event()
        self.get_audio_count = 0

    async def on_init(self, ten_env: AsyncTenEnv) -> None:
        try:
            await super().on_init(ten_env)
            ten_env.log_debug("on_init")

            if self.config is None:
                config_json, _ = await self.ten_env.get_property_to_json("")
                self.config = ElevenLabsTTS2Config.model_validate_json(
                    config_json
                )
                self.ten_env.log_debug(
                    f"Config params before update: {self.config.params}"
                )
                self.config.update_params()
                self.ten_env.log_info(
                    f"KEYPOINT config: {self.config.to_str(True)}"
                )

                if not self.config.key:
                    self.ten_env.log_error("get property key")
                    raise ValueError("key is required")

            # Create error callback function
            async def error_callback(request_id: str, error: ModuleError):
                # If no request_id is provided, use the current request_id
                target_request_id = (
                    request_id if request_id else self.current_request_id or ""
                )
                await self.send_tts_error(target_request_id, error)
                if error.code == ModuleErrorCode.FATAL_ERROR:
                    self.ten_env.log_error(
                        f"Fatal error occurred: {error.message}"
                    )
                    await self.client.close()
                    self.on_stop(self.ten_env)

            # Create client (connection management will be handled automatically)
            self.client = ElevenLabsTTS2Client(
                self.config, ten_env, error_callback, self.response_msgs
            )
            self.msg_polling_task = asyncio.create_task(self._loop())

            # Mark initialization as complete
            self.init_complete.set()
            ten_env.log_debug("Initialization completed")
        except Exception as e:
            ten_env.log_error(f"on_init failed: {traceback.format_exc()}")
            # Even if initialization fails, we should set the event to prevent infinite waiting
            self.init_complete.set()
            ten_env.log_debug(
                "Initialization failed but event set to prevent blocking"
            )
            await self.send_tts_error(
                "",  # No request_id available during on_init
                ModuleError(
                    message=str(e),
                    module=ModuleType.TTS,
                    code=ModuleErrorCode.FATAL_ERROR,
                    vendor_info={},
                ),
            )

    async def on_stop(self, ten_env: AsyncTenEnv) -> None:
        # Close client connection
        if self.client:
            await self.client.close()

        if self.msg_polling_task:
            self.msg_polling_task.cancel()

        # close all PCMWriter
        for request_id, recorder in self.recorder_map.items():
            try:
                await recorder.flush()
                ten_env.log_info(
                    f"Flushed PCMWriter for request_id: {request_id}"
                )
            except Exception as e:
                ten_env.log_error(
                    f"Error flushing PCMWriter for request_id {request_id}: {e}"
                )

        # Reset initialization event
        self.init_complete.clear()
        await super().on_stop(ten_env)
        ten_env.log_debug("on_stop")

    async def on_deinit(self, ten_env: AsyncTenEnv) -> None:
        await super().on_deinit(ten_env)
        ten_env.log_debug("on_deinit")

    def vendor(self) -> str:
        return "elevenlabs"

    def synthesize_audio_sample_rate(self) -> int:
        return self.config.sample_rate

    def synthesize_audio_channels(self) -> int:
        return 1

    def synthesize_audio_sample_width(self) -> int:
        return 2

    async def _loop(self) -> None:
        """Message polling loop"""
        while True:
            try:
                audio_data, isFinal, _, ttfb_ms = (
                    await self.client.response_msgs.get()
                )
                if ttfb_ms is not None:
                    await self.send_tts_ttfb_metrics(
                        self.current_request_id, ttfb_ms, self.current_turn_id
                    )
                self.ten_env.log_debug(f"Received isFinal: {isFinal}")
                self.get_audio_count += 1

                if audio_data is not None:
                    self.ten_env.log_info(
                        f"KEYPOINT Received audio data for request ID: {self.current_request_id}, audio_data_len: {len(audio_data)}"
                    )

                    # new request_id, send TTSAudioStart event
                    if (
                        self.current_request_id
                        and self.request_start_ts is None
                    ):
                        self.ten_env.log_info(
                            f"KEYPOINT Sent TTSAudioStart for request ID: {self.current_request_id}"
                        )
                        self.request_start_ts = datetime.now()
                        await self.send_tts_audio_start(self.current_request_id)

                    if (
                        self.config.dump
                        and self.current_request_id
                        and self.current_request_id in self.recorder_map
                    ):
                        await self.recorder_map[self.current_request_id].write(
                            audio_data
                        )
                        self.ten_env.log_debug(
                            f"Wrote {len(audio_data)} bytes to PCMWriter for request_id: {self.current_request_id}"
                        )

                    cur_duration = self.calculate_audio_duration(
                        len(audio_data),
                        self.synthesize_audio_sample_rate(),
                        self.synthesize_audio_channels(),
                        self.synthesize_audio_sample_width(),
                    )
                    if self.request_total_audio_duration is None:
                        self.request_total_audio_duration = cur_duration
                    else:
                        self.request_total_audio_duration += cur_duration

                    self.ten_env.log_debug(
                        f"get_audio_count: {self.get_audio_count}"
                    )
                    self.get_audio_count += 1
                    await self.send_tts_audio_data(audio_data)

                if isFinal and self.current_request_id:
                    await self.handle_completed_request(
                        TTSAudioEndReason.REQUEST_END
                    )
                    # Don't reset current_request_id here, let the next request set it
                    # Reset only timing-related variables

            except Exception:
                self.ten_env.log_error(
                    f"Error in _loop: {traceback.format_exc()}"
                )

    async def request_tts(self, t: TTSTextInput) -> None:
        """
        Override this method to handle TTS requests.
        This is called when the TTS request is made.
        """
        try:
            self.ten_env.log_info(
                f"KEYPOINT Requesting TTS for text: {t.text}, text_input_end: {t.text_input_end} request ID: {t.request_id}"
            )

            # check if request_id has already been completed
            if (
                self.completed_request_ids
                and t.request_id in self.completed_request_ids
            ):
                error_msg = (
                    f"Request ID {t.request_id} has already been completed "
                )
                self.ten_env.log_warn(error_msg)
                return
            if t.text_input_end == True:
                self.completed_request_ids.add(t.request_id)
                self.ten_env.log_info(
                    f"add completed request_id to: {t.request_id}"
                )

            # new request id
            if (
                self.current_request_id is None
                or t.request_id != self.current_request_id
            ):
                self.ten_env.log_info(
                    f"KEYPOINT New TTS request with ID: {t.request_id}"
                )
                self.current_request_id = t.request_id
                if (
                    self.client
                    and self.client.synthesizer
                    and self.client.synthesizer.send_text_in_connection == True
                ):
                    self.ten_env.log_info(
                        "request id is changed, but connection is not reset, reset it now"
                    )
                    self.client.cancel()
                    await self.handle_completed_request(
                        TTSAudioEndReason.INTERRUPTED
                    )

                if t.metadata is not None:
                    self.session_id = t.metadata.get("session_id", "")
                    self.current_turn_id = t.metadata.get("turn_id", -1)
                self.request_total_audio_duration = 0

                # create new PCMWriter for new request_id, and clean up old PCMWriter
                if self.config.dump:
                    # clean up old PCMWriter (except for the current new request_id)
                    old_request_ids = [
                        rid
                        for rid in self.recorder_map.keys()
                        if rid != t.request_id
                    ]
                    for old_rid in old_request_ids:
                        try:
                            await self.recorder_map[old_rid].flush()
                            del self.recorder_map[old_rid]
                            self.ten_env.log_info(
                                f"Cleaned up old PCMWriter for request_id: {old_rid}"
                            )
                        except Exception as e:
                            self.ten_env.log_error(
                                f"Error cleaning up PCMWriter for request_id {old_rid}: {e}"
                            )

                    # create new PCMWriter
                    if t.request_id not in self.recorder_map:
                        dump_file_path = os.path.join(
                            self.config.dump_path,
                            f"elevenlabs_dump_{t.request_id}.pcm",
                        )
                        self.recorder_map[t.request_id] = PCMWriter(
                            dump_file_path
                        )
                        self.ten_env.log_info(
                            f"Created PCMWriter for request_id: {t.request_id}, file: {dump_file_path}"
                        )

            # Wait for initialization to complete with timeout
            self.ten_env.log_debug(
                f"Init complete status: {self.init_complete.is_set()}"
            )
            if not self.init_complete.is_set():
                self.ten_env.log_debug(
                    "Waiting for initialization to complete..."
                )
                try:
                    await asyncio.wait_for(
                        self.init_complete.wait(), timeout=10.0
                    )  # 10 second timeout
                    self.ten_env.log_debug(
                        "Initialization completed, proceeding with TTS request"
                    )
                except asyncio.TimeoutError:
                    self.ten_env.log_error(
                        "Initialization timeout, cannot process TTS request"
                    )
                    await self.send_tts_error(
                        t.request_id,
                        ModuleError(
                            message="TTS initialization timeout",
                            module=ModuleType.TTS,
                            code=ModuleErrorCode.FATAL_ERROR,
                            vendor_info={"vendor": "elevenlabs"},
                        ),
                    )
                    return
            else:
                self.ten_env.log_debug(
                    "Initialization already completed, proceeding with TTS request"
                )

            if self.client is None:
                self.ten_env.log_error(
                    "Client is not initialized, cannot process TTS request"
                )
                await self.send_tts_error(
                    t.request_id,
                    ModuleError(
                        message="TTS client is not initialized",
                        module=ModuleType.TTS,
                        code=ModuleErrorCode.FATAL_ERROR,
                        vendor_info={"vendor": "elevenlabs"},
                    ),
                )
                return

            # Send text to client
            await self.client.send_text(t)

        except ModuleVendorException as e:
            self.ten_env.log_error(
                f"ModuleVendorException in request_tts: {traceback.format_exc()}. text: {t.text}"
            )
            await self.send_tts_error(
                self.current_request_id,
                ModuleError(
                    message=str(e),
                    module=ModuleType.TTS,
                    code=ModuleErrorCode.NON_FATAL_ERROR,
                    vendor_info=e.error,
                ),
            )
        except Exception as e:
            self.ten_env.log_error(
                f"Error in request_tts: {traceback.format_exc()}. text: {t.text}"
            )
            await self.send_tts_error(
                self.current_request_id,
                ModuleError(
                    message=str(e),
                    module=ModuleType.TTS,
                    code=ModuleErrorCode.NON_FATAL_ERROR,
                    vendor_info={"vendor": "elevenlabs"},
                ),
            )

    async def on_data(self, ten_env: AsyncTenEnv, data: Data) -> None:

        name = data.get_name()
        if name == "tts_flush":
            ten_env.log_info(f"Received tts_flush data: {name}")

            # Wait for initialization to complete with timeout
            if not self.init_complete.is_set():
                ten_env.log_debug(
                    "Waiting for initialization to complete before handling flush..."
                )
                try:
                    await asyncio.wait_for(
                        self.init_complete.wait(), timeout=30.0
                    )  # 30 second timeout
                    ten_env.log_debug(
                        "Initialization completed, proceeding with flush"
                    )
                except asyncio.TimeoutError:
                    ten_env.log_error(
                        "Initialization timeout, cannot handle flush"
                    )
                    await self.send_tts_error(
                        self.current_request_id,
                        ModuleError(
                            message="TTS initialization timeout",
                            module=ModuleType.TTS,
                            code=ModuleErrorCode.FATAL_ERROR,
                            vendor_info={"vendor": "elevenlabs"},
                        ),
                    )
                    return

            if self.client is None:
                ten_env.log_error(
                    "Client is not initialized, cannot handle flush"
                )
                await self.send_tts_error(
                    self.current_request_id,
                    ModuleError(
                        message="TTS client is not initialized",
                        module=ModuleType.TTS,
                        code=ModuleErrorCode.FATAL_ERROR,
                        vendor_info={"vendor": "elevenlabs"},
                    ),
                )
                return

            try:
                # Cancel current connection (maintain original flush disconnect behavior)
                self.client.cancel()
                await self.handle_completed_request(
                    TTSAudioEndReason.INTERRUPTED
                )
            except Exception as e:
                ten_env.log_error(f"Error in handle_flush: {e}")
                await self.send_tts_error(
                    self.current_request_id,
                    ModuleError(
                        message=str(e),
                        module=ModuleType.TTS,
                        code=ModuleErrorCode.NON_FATAL_ERROR,
                        vendor_info={"vendor": "elevenlabs"},
                    ),
                )
                return
        await super().on_data(ten_env, data)

    async def handle_completed_request(self, reason: TTSAudioEndReason):
        # update request_id
        self.completed_request_ids.add(self.current_request_id)
        self.ten_env.log_info(
            f"add completed request_id to: {self.current_request_id}"
        )

        # Flush PCMWriter for the completed request
        if (
            self.config.dump
            and self.current_request_id
            and self.current_request_id in self.recorder_map
        ):
            try:
                await self.recorder_map[self.current_request_id].flush()
                self.ten_env.log_info(
                    f"Flushed PCMWriter for completed request_id: {self.current_request_id}"
                )
            except Exception as e:
                self.ten_env.log_error(
                    f"Error flushing PCMWriter for completed request_id {self.current_request_id}: {e}"
                )

        # send audio_end
        request_event_interval = 0
        if self.request_start_ts is not None:
            request_event_interval = int(
                (datetime.now() - self.request_start_ts).total_seconds() * 1000
            )
        # Ensure request_total_audio_duration is not None
        duration_ms = (
            self.request_total_audio_duration
            if self.request_total_audio_duration is not None
            else 0
        )
        await self.send_tts_audio_end(
            self.current_request_id,
            request_event_interval,
            duration_ms,
            self.current_turn_id,
            reason,
        )
        self.ten_env.log_info(
            f"Sent tts_audio_end with {reason.name} reason for request_id: {self.current_request_id}"
        )
        self.request_start_ts = None
        self.request_total_audio_duration = None

    def calculate_audio_duration(
        self,
        bytes_length: int,
        sample_rate: int,
        channels: int = 1,
        sample_width: int = 2,
    ) -> int:
        """
        Calculate audio duration in milliseconds.

        Parameters:
        - bytes_length: Length of the audio data in bytes
        - sample_rate: Sample rate in Hz (e.g., 16000)
        - channels: Number of audio channels (default: 1 for mono)
        - sample_width: Number of bytes per sample (default: 2 for 16-bit PCM)

        Returns:
        - Duration in milliseconds (rounded down to nearest int)
        """
        bytes_per_second = sample_rate * channels * sample_width
        duration_seconds = bytes_length / bytes_per_second
        return int(duration_seconds * 1000)
