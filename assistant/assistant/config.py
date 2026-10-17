"""集中配置：全部来自环境变量，启动时校验，快速失败（ADR-0002 / 专家规范）。

密钥只出现在 .env / 环境变量中；本模块只读取，绝不落库、绝不进日志。
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Provider = Literal["mock", "openai_compatible", "ollama"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    # ── 服务 ──
    api_host: str = "127.0.0.1"
    api_port: int = 8787
    cors_allowed_origins: str = "http://127.0.0.1:5173,http://localhost:5173"
    log_level: str = "INFO"
    data_dir: Path = Path("./data")

    # ── LLM Provider（ADR-0005：默认 mock，无密钥完整复现） ──
    llm_provider: Provider = "mock"
    llm_base_url: str = "https://api.deepseek.com/v1"
    llm_api_key: SecretStr | None = None
    llm_model: str = "deepseek-chat"

    # ── 认知周期预算（论文 4.4 / ADR-0005） ──
    deep_cycles_per_day: int = Field(default=2, ge=0, le=24)
    daily_token_budget: int = Field(default=200_000, ge=0)
    light_observe_interval_minutes: int = Field(default=15, ge=1)

    # ── 采集源（逗号分隔；本地优先，ADR-0004） ──
    collector_ics_paths: str = ""
    collector_notes_paths: str = ""
    collector_rss_urls: str = ""
    consent_granted_by: str = "owner"

    @field_validator("log_level")
    @classmethod
    def _valid_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR"}
        v = v.upper()
        if v not in allowed:
            raise ValueError(f"log_level 必须是 {allowed} 之一")
        return v

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    @property
    def db_path(self) -> Path:
        return self.data_dir / "assistant.db"

    @property
    def ics_paths(self) -> list[Path]:
        return [Path(p.strip()) for p in self.collector_ics_paths.split(",") if p.strip()]

    @property
    def notes_paths(self) -> list[Path]:
        return [Path(p.strip()) for p in self.collector_notes_paths.split(",") if p.strip()]

    @property
    def rss_urls(self) -> list[str]:
        return [u.strip() for u in self.collector_rss_urls.split(",") if u.strip()]

    def validate_for_startup(self) -> None:
        """启动时集中校验；任何不满足直接抛 ConfigurationError（快速失败）。"""
        from assistant.errors import ConfigurationError

        if self.llm_provider != "mock":
            if not self.llm_base_url:
                raise ConfigurationError("非 mock 模式必须提供 LLM_BASE_URL")
            if not self.llm_api_key:
                raise ConfigurationError("非 mock 模式必须提供 LLM_API_KEY")
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            probe = self.data_dir / ".write_probe"
            probe.touch()
            probe.unlink()
        except OSError as e:
            raise ConfigurationError(f"data_dir 不可写: {self.data_dir} ({e})") from e


@lru_cache
def get_settings() -> Settings:
    return Settings()


def reset_settings_cache() -> None:
    """测试用：清空配置缓存。"""
    get_settings.cache_clear()


# 便于脚本直接读环境（不经过 Settings 校验的场景）
def env_flag(name: str, default: bool = False) -> bool:
    return os.getenv(name, "").lower() in {"1", "true", "yes", "on"} or default
