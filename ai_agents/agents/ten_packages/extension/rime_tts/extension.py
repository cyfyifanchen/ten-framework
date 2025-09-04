#
# This file is part of TEN Framework, an open source project.
# Licensed under the Apache License, Version 2.0.
# See the LICENSE file for more information.
#
import asyncio
from datetime import datetime
import os
import traceback

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
from .config import RimeTTSConfig

from .rime_tts import (
    EVENT_TTS_END,
    EVENT_TTS_RESPONSE,
    EVENT_TTS_TTFB_METRIC,
    RimeTTSClient,
)
from ten_runtime import (
    AsyncTenEnv,
    Data,
)


class RimeTTSExtension(AsyncTTS2BaseExtension):
    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.config: RimeTTSConfig = None
        self.client: RimeTTSClient = None
        self.current_request_id: str = None
        self.current_turn_id: int = -1
        self.stop_event: asyncio.Event = None
        self.msg_polling_task: asyncio.Task = None
        self.recorder: PCMWriter = None
        self.request_start_ts: datetime | None = None
        self.request_ttfb: int | None = None
        self.request_total_audio_duration: int = 0
        self.response_msgs = asyncio.Queue[tuple[int, bytes | int]]()
        self.recorder_map: dict[str, PCMWriter] = (
            {}
        )  # 存储不同 request_id 对应的 PCMWriter
        self.last_completed_request_id: str | None = (
            None  # 最新完成的 request_id
        )
        self.last_completed_has_reset_synthesizer = True

    async def on_init(self, ten_env: AsyncTenEnv) -> None:
        try:
            await super().on_init(ten_env)
            ten_env.log_debug("on_init")

            if self.config is None:
                config_json, _ = await self.ten_env.get_property_to_json("")
                self.config = RimeTTSConfig.model_validate_json(config_json)
                self.config.update_params()
                self.ten_env.log_info(
                    f"KEYPOINT config: {self.config.to_str()}"
                )

                # extract parameters from config

                if not self.config.api_key:
                    self.ten_env.log_error(
                        "Configuration is empty. Required parameter 'api_key' is missing."
                    )
                    raise ValueError(
                        "Configuration is empty. Required parameter 'api_key' is missing."
                    )

            # Create client (connection management will be handled automatically)
            self.client = RimeTTSClient(
                self.config, self.ten_env, self.vendor(), self.response_msgs
            )
            self.msg_polling_task = asyncio.create_task(self._loop())
        except Exception as e:
            ten_env.log_error(f"on_start failed: {traceback.format_exc()}")
            await self.send_tts_error(
                self.current_request_id or "",
                ModuleError(
                    message=str(e),
                    module=ModuleType.TTS,
                    code=ModuleErrorCode.FATAL_ERROR,
                    vendor_info={},
                ),
            )

    async def on_stop(self, ten_env: AsyncTenEnv) -> None:
        # 关闭客户端连接
        if self.client:
            await self.client.close()

        if self.msg_polling_task:
            self.msg_polling_task.cancel()

        # 关闭所有 PCMWriter
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

        await super().on_stop(ten_env)
        ten_env.log_debug("on_stop")

    async def on_deinit(self, ten_env: AsyncTenEnv) -> None:
        await super().on_deinit(ten_env)
        ten_env.log_debug("on_deinit")

    def vendor(self) -> str:
        return "rime"

    def synthesize_audio_sample_rate(self) -> int:
        return self.config.sampling_rate

    async def _loop(self) -> None:
        while True:
            try:
                event, data = await self.client.response_msgs.get()

                if event == EVENT_TTS_RESPONSE:  # Audio data event
                    if data is not None and isinstance(data, bytes):
                        self.ten_env.log_info(
                            f"KEYPOINT Received audio data for request ID: {self.current_request_id}, audio_data_len: {len(data)}"
                        )

                        if (
                            self.config.dump
                            and self.current_request_id
                            and self.current_request_id in self.recorder_map
                        ):
                            asyncio.create_task(
                                self.recorder_map[
                                    self.current_request_id
                                ].write(data)
                            )
                        self.request_total_audio_duration += (
                            self.calculate_audio_duration(
                                len(data),
                                self.synthesize_audio_sample_rate(),
                                self.synthesize_audio_channels(),
                                self.synthesize_audio_sample_width(),
                            )
                        )
                        await self.send_tts_audio_data(data)
                    else:
                        self.ten_env.log_error(
                            "Received empty payload for TTS response"
                        )
                elif event == EVENT_TTS_TTFB_METRIC:
                    if data is not None and isinstance(data, int):
                        self.request_start_ts = datetime.now()
                        ttfb = data
                        await self.send_tts_audio_start(self.current_request_id)
                        await self.send_tts_ttfb_metrics(
                            self.current_request_id,
                            ttfb,
                            self.current_turn_id,
                        )

                        self.ten_env.log_info(
                            f"KEYPOINT Sent TTS audio start and TTFB metrics: {ttfb}ms"
                        )
                elif event == EVENT_TTS_END:
                    self.ten_env.log_info(
                        f"KEYPOINT Session finished for request ID: {self.current_request_id}"
                    )
                    if self.request_start_ts is not None:
                        request_event_interval = int(
                            (
                                datetime.now() - self.request_start_ts
                            ).total_seconds()
                            * 1000
                        )
                        await self.send_tts_audio_end(
                            self.current_request_id,
                            request_event_interval,
                            self.request_total_audio_duration,
                            self.current_turn_id,
                        )

                        self.ten_env.log_info(
                            f"KEYPOINT request time stamped for request ID: {self.current_request_id}, request_event_interval: {request_event_interval}ms, total_audio_duration: {self.request_total_audio_duration}ms"
                        )
                    if self.stop_event:
                        self.stop_event.set()
                        self.stop_event = None

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

            # 检查是否已经收到过这个 request_id 的 text_input_end=true
            if (
                self.last_completed_request_id
                and t.request_id == self.last_completed_request_id
            ):
                error_msg = f"Request ID {t.request_id} has already been completed (last completed: {self.last_completed_request_id})"
                self.ten_env.log_warn(error_msg)
                await self.send_tts_error(
                    t.request_id,
                    ModuleError(
                        message=error_msg,
                        module=ModuleType.TTS,
                        code=ModuleErrorCode.NON_FATAL_ERROR,
                        vendor_info=None,
                    ),
                )
                return
            if t.request_id != self.current_request_id:
                self.ten_env.log_info(
                    f"KEYPOINT New TTS request with ID: {t.request_id}"
                )
                if not self.last_completed_has_reset_synthesizer:
                    self.client.reset_synthesizer()
                self.last_completed_has_reset_synthesizer = False

                self.current_request_id = t.request_id
                if t.metadata is not None:
                    self.session_id = t.metadata.get("session_id", "")
                    self.current_turn_id = t.metadata.get("turn_id", -1)
                self.request_start_ts = datetime.now()
                self.request_total_audio_duration = 0

                # 为新 request_id 创建新的 PCMWriter，并清理旧的
                if self.config.dump:
                    # 清理旧的 PCMWriter（除了当前新的 request_id）
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

                    # 创建新的 PCMWriter
                    if t.request_id not in self.recorder_map:
                        dump_file_path = os.path.join(
                            self.config.dump_path,
                            f"rime_dump_{t.request_id}.pcm",
                        )
                        self.recorder_map[t.request_id] = PCMWriter(
                            dump_file_path
                        )
                        self.ten_env.log_info(
                            f"Created PCMWriter for request_id: {t.request_id}, file: {dump_file_path}"
                        )

            if t.text.strip() != "":
                await self.client.send_text(t)
            if t.text_input_end:
                self.ten_env.log_info(
                    f"KEYPOINT finish session for request ID: {t.request_id}"
                )

                # 更新最新完成的 request_id
                self.last_completed_request_id = t.request_id
                self.ten_env.log_info(
                    f"Updated last completed request_id to: {t.request_id}"
                )

                self.stop_event = asyncio.Event()
                await self.stop_event.wait()

                # session finished, connection will be re-established for next request
                if not self.last_completed_has_reset_synthesizer:
                    self.client.reset_synthesizer()
                    self.last_completed_has_reset_synthesizer = True

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
                    vendor_info={},
                ),
            )

    async def on_data(self, ten_env: AsyncTenEnv, data: Data) -> None:
        name = data.get_name()
        if name == "tts_flush":
            # Cancel current connection (maintain original flush disconnect behavior)
            if self.client:
                self.client.cancel()
                self.last_completed_has_reset_synthesizer = True

            # If there's a waiting stop_event, set it to release request_tts waiting
            if self.stop_event:
                self.stop_event.set()
                self.stop_event = None

            ten_env.log_info(f"Received tts_flush data: {name}")
            if self.request_start_ts is not None:
                request_event_interval = int(
                    (datetime.now() - self.request_start_ts).total_seconds()
                    * 1000
                )
                await self.send_tts_audio_end(
                    self.current_request_id,
                    request_event_interval,
                    self.request_total_audio_duration,
                    self.current_turn_id,
                    TTSAudioEndReason.INTERRUPTED,
                )
            ten_env.log_info(
                f"Sent tts_audio_end with INTERRUPTED reason for request_id: {self.current_request_id}"
            )
        await super().on_data(ten_env, data)

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
