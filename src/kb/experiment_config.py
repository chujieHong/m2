"""Day 8：统一实验配置，下一步由实验入口读取。"""
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class ExperimentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    name: str = Field(min_length=1)
    collection: str = Field(min_length=1)
    embedding_model: str = Field(min_length=1)
    chat_model: str = Field(min_length=1)
    top_k: int = Field(gt=0)
    temperature: float = Field(ge=0, le=2)
    max_tokens: int = Field(gt=0)


def load_experiment_config(path: Path) -> ExperimentConfig:
    return ExperimentConfig.model_validate_json(
        path.read_text(encoding="utf-8")
    )