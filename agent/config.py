"""大模型配置 - 统一管理 base_url、api_key、model 等参数"""

from dataclasses import dataclass
import os
from typing import Optional

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class LLMConfig:
    """大模型运行配置"""

    provider: str
    api_key: str
    model: str
    base_url: Optional[str] = None
    temperature: float = 0.7
    timeout: int = 15

    @property
    def is_configured(self) -> bool:
        """是否已配置可用的 API Key"""
        return bool(self.api_key)


def _get_float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _get_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def get_llm_config(
    model_name: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> LLMConfig:
    """获取统一的大模型配置。

    优先级：显式参数 > 环境变量 > 默认值。

    支持：
    - OpenAI / OpenAI-compatible: OPENAI_API_KEY, OPENAI_MODEL, OPENAI_BASE_URL
    - 通义千问 OpenAI 兼容模式: DASHSCOPE_API_KEY, DASHSCOPE_MODEL, DASHSCOPE_BASE_URL
    - 通用别名: LLM_API_KEY, LLM_MODEL, LLM_BASE_URL
    """

    provider = os.getenv("LLM_PROVIDER", "openai").strip().lower()

    resolved_api_key = (
        api_key
        if api_key is not None
        else os.getenv("LLM_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("DASHSCOPE_API_KEY")
        or ""
    )

    resolved_model = (
        model_name
        or os.getenv("LLM_MODEL")
        or os.getenv("OPENAI_MODEL")
        or os.getenv("DASHSCOPE_MODEL")
        or "gpt-4o-mini"
    )

    resolved_base_url = (
        base_url
        if base_url is not None
        else os.getenv("LLM_BASE_URL")
        or os.getenv("OPENAI_BASE_URL")
        or os.getenv("DASHSCOPE_BASE_URL")
        or None
    )

    return LLMConfig(
        provider=provider,
        api_key=resolved_api_key,
        model=resolved_model,
        base_url=resolved_base_url,
        temperature=_get_float_env("LLM_TEMPERATURE", 0.7),
        timeout=_get_int_env("LLM_TIMEOUT", 15),
    )


def build_chat_openai_kwargs(config: LLMConfig) -> dict:
    """转换为 ChatOpenAI 初始化参数。"""

    kwargs = {
        "model": config.model,
        "api_key": config.api_key,
        "temperature": config.temperature,
    }
    if config.base_url:
        kwargs["base_url"] = config.base_url
    return kwargs
