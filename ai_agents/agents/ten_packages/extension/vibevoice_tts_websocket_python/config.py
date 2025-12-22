from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class VibeVoiceTTSConfig(BaseModel):
    url: str = "ws://127.0.0.1:3000/stream"
    cfg_scale: float = 1.5
    steps: Optional[int] = None
    voice: Optional[str] = None
    sample_rate: int = 24000
    channels: int = 1
    sample_width: int = 2
    dump: bool = False
    dump_path: str = ""
    params: Dict[str, Any] = Field(default_factory=dict)
    black_list_params: List[str] = Field(default_factory=list)

    def is_black_list_params(self, key: str) -> bool:
        return key in self.black_list_params

    def update_params(self) -> None:
        if "url" in self.params:
            self.url = str(self.params.pop("url"))

        if "cfg_scale" in self.params:
            try:
                self.cfg_scale = float(self.params.pop("cfg_scale"))
            except (TypeError, ValueError):
                self.params.pop("cfg_scale", None)

        if "steps" in self.params:
            try:
                self.steps = int(self.params.pop("steps"))
            except (TypeError, ValueError):
                self.steps = None
                self.params.pop("steps", None)

        if "voice" in self.params:
            voice_val = self.params.pop("voice")
            self.voice = str(voice_val) if voice_val is not None else None

        if "sample_rate" in self.params:
            try:
                self.sample_rate = int(self.params.pop("sample_rate"))
            except (TypeError, ValueError):
                self.params.pop("sample_rate", None)

        if "channels" in self.params:
            try:
                self.channels = int(self.params.pop("channels"))
            except (TypeError, ValueError):
                self.params.pop("channels", None)

        if "sample_width" in self.params:
            try:
                self.sample_width = int(self.params.pop("sample_width"))
            except (TypeError, ValueError):
                self.params.pop("sample_width", None)

    def to_str(self, sensitive_handling: bool = False) -> str:
        return f"{self}"
