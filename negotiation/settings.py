from dataclasses import dataclass

from negotiation.records import SettingsRecord
from negotiation.scoring import MAX_PENALTY

DEFAULT_MODELS: tuple[str, ...] = (
    "deepseek/deepseek-v4.1-flash",
    "nvidia/nemotron-3-super-120b-a12b",
    "openai/gpt-oss-120b",
)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


@dataclass(frozen=True)
class MatchSettings:
    turns_per_side: int = 10
    message_char_limit: int = 1_000
    max_penalty: float = MAX_PENALTY
    max_output_tokens: int = 4_000
    temperature: float | None = None
    request_attempts: int = 4

    def to_record(self) -> SettingsRecord:
        return {
            "turns_per_side": self.turns_per_side,
            "message_char_limit": self.message_char_limit,
            "max_penalty": self.max_penalty,
            "max_output_tokens": self.max_output_tokens,
            "temperature": self.temperature,
            "request_attempts": self.request_attempts,
        }

    @classmethod
    def from_record(cls, record: SettingsRecord) -> "MatchSettings":
        return cls(**record)
