import asyncio
import json
import time
from typing import Literal, Optional

from .agent.decorators import agent_event_handler
from ten_runtime import (
    AsyncExtension,
    AsyncTenEnv,
    Cmd,
    Data,
)

from .agent.agent import Agent
from .agent.events import (
    ASRResultEvent,
    LLMResponseEvent,
    ToolRegisterEvent,
    UserJoinedEvent,
    UserLeftEvent,
)
from .helper import _send_cmd, _send_data, parse_sentences
from .config import MainControlConfig  # assume extracted from your base model

import uuid


class MainControlExtension(AsyncExtension):
    """
    The entry point of the agent module.
    Consumes semantic AgentEvents from the Agent class and drives the runtime behavior.
    """

    def __init__(self, name: str):
        super().__init__(name)
        self.ten_env: AsyncTenEnv = None
        self.agent: Agent = None
        self.config: MainControlConfig = None

        self.stopped: bool = False
        self._rtc_user_count: int = 0
        self.sentence_fragment: str = ""
        self.turn_id: int = 0
        self.session_id: str = "0"
        self.last_speaker: str = ""  # Track the last speaker for context
        # === Game state for "Who Said What" ===
        self.player_names: list[str] = ["Elliot", "Trump", "Musk"]
        self.speaker_assignments: dict[str, str] = {}
        self.enrollment_prompted: bool = False
        self.enrollment_complete: bool = False
        self.pending_response_target: Optional[str] = None
        self.last_enrollment_reminder_ts: float = 0.0
        self.last_unknown_speaker_ts: float = 0.0

    def _current_metadata(self) -> dict:
        return {"session_id": self.session_id, "turn_id": self.turn_id}

    async def on_init(self, ten_env: AsyncTenEnv):
        self.ten_env = ten_env

        # Load config from runtime properties
        config_json, _ = await ten_env.get_property_to_json(None)
        self.config = MainControlConfig.model_validate_json(config_json)

        self.agent = Agent(ten_env)

        # Now auto-register decorated methods
        for attr_name in dir(self):
            fn = getattr(self, attr_name)
            event_type = getattr(fn, "_agent_event_type", None)
            if event_type:
                self.agent.on(event_type, fn)

    # === Register handlers with decorators ===
    @agent_event_handler(UserJoinedEvent)
    async def _on_user_joined(self, event: UserJoinedEvent):
        self._rtc_user_count += 1
        if self._rtc_user_count == 1 and self.config and self.config.greeting:
            await self._send_to_tts(self.config.greeting, True)
            # No label for assistant greeting
            await self._send_transcript(
                "assistant", self.config.greeting, True, 100
            )
        if not self.enrollment_prompted:
            await self._prompt_enrollment()

    @agent_event_handler(UserLeftEvent)
    async def _on_user_left(self, event: UserLeftEvent):
        self._rtc_user_count -= 1

    @agent_event_handler(ToolRegisterEvent)
    async def _on_tool_register(self, event: ToolRegisterEvent):
        await self.agent.register_llm_tool(event.tool, event.source)

    @agent_event_handler(ASRResultEvent)
    async def _on_asr_result(self, event: ASRResultEvent):
        self.session_id = event.metadata.get("session_id", "100")
        stream_id = int(self.session_id)

        # Extract speaker information for diarization
        speaker = event.metadata.get("speaker", "")
        channel = event.metadata.get("channel", "")
        speaker_str = self._normalize_label(speaker)
        channel_str = self._normalize_label(channel)
        speaker_key = self._build_speaker_key(speaker_str, channel_str)

        # Debug logging to check if speaker info is received
        if event.final:
            self.ten_env.log_info(f"[ASR] Received metadata: speaker='{speaker}', channel='{channel}', metadata={event.metadata}")

        # Format speaker label as [S1], [S2], etc.
        speaker_label = ""
        assigned_name = (
            self.speaker_assignments[speaker_key]
            if speaker_key and speaker_key in self.speaker_assignments
            else None
        )
        if assigned_name:
            speaker_label = f"[{assigned_name}] "
            self.ten_env.log_info(
                f"[ASR] Using enrolled label: {speaker_label}"
            )
        elif speaker_str:
            speaker_label = f"[{speaker_str}] "
            self.ten_env.log_info(f"[ASR] Using speaker label: {speaker_label}")
        elif channel_str:
            speaker_label = f"[{channel_str}] "
            self.ten_env.log_info(f"[ASR] Using channel label: {speaker_label}")
        else:
            # If no speaker/channel info, use last known speaker or default
            if self.last_speaker:
                speaker_label = f"[{self.last_speaker}] "
                self.ten_env.log_info(f"[ASR] Using last speaker label: {speaker_label}")
            else:
                speaker_label = "[USER] "
                self.ten_env.log_info(f"[ASR] Using default label: {speaker_label}")

        if not event.text:
            return
        if event.final or len(event.text) > 2:
            await self._interrupt()
        queue_text: Optional[str] = None
        if event.final:
            self.turn_id += 1
            # Track the current speaker
            resolved_label = speaker_str if speaker_str else channel_str
            registered_name = await self._assign_player_if_needed(speaker_key)
            if registered_name:
                assigned_name = registered_name
                speaker_label = f"[{assigned_name}] "
            elif speaker_key and speaker_key in self.speaker_assignments:
                assigned_name = self.speaker_assignments[speaker_key]
                speaker_label = f"[{assigned_name}] "
            if assigned_name:
                resolved_label = assigned_name
            if resolved_label:
                self.last_speaker = resolved_label

            if not self.enrollment_complete:
                await self._maybe_remind_pending_players()
            else:
                if assigned_name:
                    self.pending_response_target = assigned_name
                    queue_text = (
                        f"{assigned_name} says: {event.text}\n"
                        f"Respond directly to {assigned_name}."
                    )
                else:
                    await self._handle_unknown_speaker(event.text)

        if queue_text:
            await self.agent.queue_llm_input(queue_text)

        # Add speaker label to transcript display (always include label)
        transcript_text = f"{speaker_label}{event.text}"
        self.ten_env.log_info(f"[ASR] Sending transcript: {transcript_text}")
        await self._send_transcript("user", transcript_text, event.final, stream_id)

    @agent_event_handler(LLMResponseEvent)
    async def _on_llm_response(self, event: LLMResponseEvent):
        target_player = self.pending_response_target
        if not event.is_final and event.type == "message":
            sentences, self.sentence_fragment = parse_sentences(
                self.sentence_fragment, event.delta
            )
            for s in sentences:
                if target_player:
                    await self._send_to_tts(s, False, target_player)

        if event.is_final and event.type == "message":
            remaining_text = self.sentence_fragment or ""
            self.sentence_fragment = ""
            if target_player and remaining_text:
                await self._send_to_tts(remaining_text, True, target_player)
            # Clear target when the turn is done
            self.pending_response_target = None

        # No label for assistant responses
        display_text = event.text
        if target_player and display_text:
            display_text = f"[{target_player}] {display_text}"
        await self._send_transcript(
            "assistant",
            display_text,
            event.is_final,
            100,
            data_type=("reasoning" if event.type == "reasoning" else "text"),
        )

    @staticmethod
    def _normalize_label(value) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            value = value.strip()
        if value == "":
            return ""
        return str(value).upper()

    def _build_speaker_key(self, speaker: str, channel: str) -> str:
        if speaker:
            return f"speaker:{speaker}"
        if channel:
            return f"channel:{channel}"
        return ""

    async def _prompt_enrollment(self):
        """
        Guide the players through the initial enrollment pass so diarization can map voices.
        """
        self.enrollment_prompted = True
        instructions = (
            "Welcome to Who Said What. Elliot, Trump, and Kanye, please each say something so I can learn your voices."
        )
        await self._send_to_tts(instructions, True)
        await self._send_transcript("assistant", instructions, True, 100)

    async def _assign_player_if_needed(self, speaker_key: str) -> Optional[str]:
        """
        Attach the diarization speaker key to the next available player name.
        """
        if not speaker_key:
            return None
        if speaker_key in self.speaker_assignments:
            return self.speaker_assignments[speaker_key]

        if len(self.speaker_assignments) >= len(self.player_names):
            return None

        player_name = self.player_names[len(self.speaker_assignments)]
        self.speaker_assignments[speaker_key] = player_name
        self.ten_env.log_info(
            f"[Enrollment] Registered {speaker_key} as {player_name}"
        )

        await self._announce_enrollment(player_name)

        if len(self.speaker_assignments) == len(self.player_names):
            self.enrollment_complete = True
            await self._announce_enrollment_completion()

        return player_name

    async def _announce_enrollment(self, player_name: str):
        confirmation = f"Great, I now know {player_name}'s voice."
        await self._send_transcript("assistant", confirmation, True, 100)
        await self._send_to_tts(confirmation, True)

    async def _announce_enrollment_completion(self):
        wrap_up = "All players are registered. When you speak, I will reply only to you."
        await self._send_transcript("assistant", wrap_up, True, 100)
        await self._send_to_tts(wrap_up, True)

    async def _maybe_remind_pending_players(self):
        """
        Periodically remind everyone which players still need to enroll.
        """
        remaining = [
            name
            for name in self.player_names
            if name not in self.speaker_assignments.values()
        ]
        if not remaining:
            return

        now = time.time()
        if now - self.last_enrollment_reminder_ts < 5:
            return

        self.last_enrollment_reminder_ts = now
        if len(remaining) == 1:
            reminder = f"Waiting for {remaining[0]} to check in."
        elif len(remaining) == 2:
            reminder = f"Waiting for {remaining[0]} and {remaining[1]} to check in."
        else:
            reminder = "Waiting for Elliot, Trump, and Musk to check in."

        await self._send_transcript("assistant", reminder, True, 100)
        await self._send_to_tts(reminder, True)

    async def _handle_unknown_speaker(self, text: str):
        """
        Notify the room when speech comes from an unregistered voice.
        """
        now = time.time()
        if now - self.last_unknown_speaker_ts < 5:
            self.ten_env.log_warn(
                "[MainControlExtension] Ignoring unknown speaker (rate limited)."
            )
            return

        self.last_unknown_speaker_ts = now
        message = (
            "I don't recognize that voice. Only Elliot, Trump, and Musk can play."
        )
        await self._send_transcript("assistant", message, True, 100)
        await self._send_to_tts(message, True)
        self.ten_env.log_warn(
            f"[MainControlExtension] Unrecognized speaker for text='{text}'"
        )

    async def on_start(self, ten_env: AsyncTenEnv):
        ten_env.log_info("[MainControlExtension] on_start")

    async def on_stop(self, ten_env: AsyncTenEnv):
        ten_env.log_info("[MainControlExtension] on_stop")
        self.stopped = True
        await self.agent.stop()

    async def on_cmd(self, ten_env: AsyncTenEnv, cmd: Cmd):
        await self.agent.on_cmd(cmd)

    async def on_data(self, ten_env: AsyncTenEnv, data: Data):
        await self.agent.on_data(data)

    # === helpers ===
    async def _send_transcript(
        self,
        role: str,
        text: str,
        final: bool,
        stream_id: int,
        data_type: Literal["text", "reasoning"] = "text",
    ):
        """
        Sends the transcript (ASR or LLM output) to the message collector.
        """
        if data_type == "text":
            await _send_data(
                self.ten_env,
                "message",
                "message_collector",
                {
                    "data_type": "transcribe",
                    "role": role,
                    "text": text,
                    "text_ts": int(time.time() * 1000),
                    "is_final": final,
                    "stream_id": stream_id,
                },
            )
        elif data_type == "reasoning":
            await _send_data(
                self.ten_env,
                "message",
                "message_collector",
                {
                    "data_type": "raw",
                    "role": role,
                    "text": json.dumps(
                        {
                            "type": "reasoning",
                            "data": {
                                "text": text,
                            },
                        }
                    ),
                    "text_ts": int(time.time() * 1000),
                    "is_final": final,
                    "stream_id": stream_id,
                },
            )
        self.ten_env.log_info(
            f"[MainControlExtension] Sent transcript: {role}, final={final}, text={text}"
        )

    async def _send_to_tts(
        self, text: str, is_final: bool, target_player: Optional[str] = None
    ):
        """
        Sends a sentence to the TTS system.
        """
        request_id = f"tts-request-{self.turn_id}-{uuid.uuid4().hex[:8]}"
        metadata = self._current_metadata()
        if target_player:
            metadata = {**metadata, "target_player": target_player}
        await _send_data(
            self.ten_env,
            "tts_text_input",
            "tts",
            {
                "request_id": request_id,
                "text": text,
                "text_input_end": is_final,
                "metadata": metadata,
            },
        )
        self.ten_env.log_info(
            f"[MainControlExtension] Sent to TTS: is_final={is_final}, text={text}"
        )

    async def _interrupt(self):
        """
        Interrupts ongoing LLM and TTS generation. Typically called when user speech is detected.
        """
        self.sentence_fragment = ""
        await self.agent.flush_llm()
        await _send_data(
            self.ten_env, "tts_flush", "tts", {"flush_id": str(uuid.uuid4())}
        )
        await _send_cmd(self.ten_env, "flush", "agora_rtc")
        self.ten_env.log_info("[MainControlExtension] Interrupt signal sent")
