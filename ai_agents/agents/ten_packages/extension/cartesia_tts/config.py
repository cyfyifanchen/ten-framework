from typing import Any
import copy
from ten_ai_base import utils

from pydantic import BaseModel, Field


class CartesiaSSMLConfig(BaseModel):
    enabled: bool = False
    speed_ratio: float | None = None
    volume_ratio: float | None = None
    emotion: str | None = None
    pre_break_time: str | None = None
    post_break_time: str | None = None
    spell_words: list[str] = Field(default_factory=list)

    def normalize(self) -> None:
        def clamp(value: Any, lower: float, upper: float) -> float | None:
            if value is None:
                return None
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                return None
            if numeric < lower:
                return lower
            if numeric > upper:
                return upper
            return numeric

        self.speed_ratio = clamp(self.speed_ratio, 0.6, 1.5)
        self.volume_ratio = clamp(self.volume_ratio, 0.5, 2.0)

        if isinstance(self.emotion, str):
            self.emotion = self.emotion.strip() or None
        else:
            self.emotion = None

        for attr in ("pre_break_time", "post_break_time"):
            value = getattr(self, attr)
            if value is None:
                continue
            if isinstance(value, str):
                stripped = value.strip()
                setattr(self, attr, stripped or None)
            else:
                setattr(self, attr, str(value))

        cleaned_spell_words: list[str] = []
        for word in self.spell_words:
            if isinstance(word, str):
                trimmed = word.strip()
                if trimmed and trimmed not in cleaned_spell_words:
                    cleaned_spell_words.append(trimmed)
        self.spell_words = cleaned_spell_words


class CartesiaTTSConfig(BaseModel):
    api_key: str = ""

    sample_rate: int = 16000
    dump: bool = False
    dump_path: str = "/tmp"
    params: dict[str, Any] = Field(default_factory=dict)
    ssml: CartesiaSSMLConfig = Field(default_factory=CartesiaSSMLConfig)

    def update_params(self) -> None:
        # Remove params that are not used
        if "transcript" in self.params:
            del self.params["transcript"]

        if "api_key" in self.params:
            self.api_key = self.params["api_key"]
            del self.params["api_key"]

        # Remove params that are not used
        if "context_id" in self.params:
            del self.params["context_id"]

        # Remove params that are not used
        if "stream" in self.params:
            del self.params["stream"]

        # Use default sample rate value
        if "sample_rate" in self.params:
            self.sample_rate = self.params["sample_rate"]
            # Remove sample_rate from params to avoid parameter error
            del self.params["sample_rate"]

        if "output_format" not in self.params:
            self.params["output_format"] = {}

        # Use custom sample rate value
        if "sample_rate" in self.params["output_format"]:
            self.sample_rate = self.params["output_format"]["sample_rate"]
        else:
            self.params["output_format"]["sample_rate"] = self.sample_rate

        ##### use fixed value #####
        self.params["output_format"]["container"] = "raw"
        self.params["output_format"]["encoding"] = "pcm_s16le"

        # Ensure generation_config defaults exist so speed/volume are always valid.
        generation_config = self.params.setdefault("generation_config", {})
        if "speed" not in generation_config:
            generation_config["speed"] = 1.0
        if "volume" not in generation_config:
            generation_config["volume"] = 1.0

        # Extract accidental SSML configs from params and normalise.
        if "ssml" in self.params:
            if isinstance(self.params["ssml"], dict):
                self.ssml = CartesiaSSMLConfig(**self.params["ssml"])
            del self.params["ssml"]

        self.ssml.normalize()

    def to_str(self, sensitive_handling: bool = True) -> str:
        """
        Convert the configuration to a string representation, masking sensitive data.
        """
        if not sensitive_handling:
            return f"{self}"

        config = copy.deepcopy(self)

        # Encrypt sensitive fields
        if config.api_key:
            config.api_key = utils.encrypt(config.api_key)
        if config.params and "api_key" in config.params:
            config.params["api_key"] = utils.encrypt(config.params["api_key"])

        return f"{config}"
