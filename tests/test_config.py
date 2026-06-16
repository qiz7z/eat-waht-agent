"""大模型配置测试"""

from unittest.mock import patch

from agent.config import build_chat_openai_kwargs, get_llm_config


class TestLLMConfig:
    """测试大模型配置"""

    def test_default_config_without_env(self):
        """测试无环境变量时的默认配置"""
        with patch.dict("os.environ", {}, clear=True):
            config = get_llm_config()
            assert config.provider == "openai"
            assert config.api_key == ""
            assert config.model == "gpt-4o-mini"
            assert config.base_url is None
            assert config.temperature == 0.7
            assert config.timeout == 15
            assert config.is_configured is False

    def test_llm_env_has_highest_priority(self):
        """测试 LLM_* 环境变量优先于 OPENAI_* 和 DASHSCOPE_*"""
        with patch.dict(
            "os.environ",
            {
                "LLM_API_KEY": "llm-key",
                "LLM_MODEL": "llm-model",
                "LLM_BASE_URL": "https://llm.example.com/v1",
                "OPENAI_API_KEY": "openai-key",
                "OPENAI_MODEL": "openai-model",
                "OPENAI_BASE_URL": "https://openai.example.com/v1",
                "DASHSCOPE_API_KEY": "dashscope-key",
                "DASHSCOPE_MODEL": "dashscope-model",
            },
            clear=True,
        ):
            config = get_llm_config()
            assert config.api_key == "llm-key"
            assert config.model == "llm-model"
            assert config.base_url == "https://llm.example.com/v1"
            assert config.is_configured is True

    def test_openai_env_fallback(self):
        """测试 OpenAI 环境变量兜底"""
        with patch.dict(
            "os.environ",
            {
                "OPENAI_API_KEY": "openai-key",
                "OPENAI_MODEL": "gpt-4o-mini",
                "OPENAI_BASE_URL": "https://api.openai.com/v1",
            },
            clear=True,
        ):
            config = get_llm_config()
            assert config.api_key == "openai-key"
            assert config.model == "gpt-4o-mini"
            assert config.base_url == "https://api.openai.com/v1"

    def test_dashscope_env_fallback(self):
        """测试通义千问环境变量兜底"""
        with patch.dict(
            "os.environ",
            {
                "DASHSCOPE_API_KEY": "dashscope-key",
                "DASHSCOPE_MODEL": "qwen-turbo",
                "DASHSCOPE_BASE_URL": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            },
            clear=True,
        ):
            config = get_llm_config()
            assert config.api_key == "dashscope-key"
            assert config.model == "qwen-turbo"
            assert config.base_url == "https://dashscope.aliyuncs.com/compatible-mode/v1"

    def test_explicit_args_override_env(self):
        """测试显式参数优先级最高"""
        with patch.dict(
            "os.environ",
            {
                "LLM_API_KEY": "env-key",
                "LLM_MODEL": "env-model",
                "LLM_BASE_URL": "https://env.example.com/v1",
            },
            clear=True,
        ):
            config = get_llm_config(
                api_key="arg-key",
                model_name="arg-model",
                base_url="https://arg.example.com/v1",
            )
            assert config.api_key == "arg-key"
            assert config.model == "arg-model"
            assert config.base_url == "https://arg.example.com/v1"

    def test_build_chat_openai_kwargs(self):
        """测试 ChatOpenAI 参数构建"""
        with patch.dict(
            "os.environ",
            {
                "LLM_API_KEY": "test-key",
                "LLM_MODEL": "test-model",
                "LLM_BASE_URL": "https://test.example.com/v1",
                "LLM_TEMPERATURE": "0.2",
            },
            clear=True,
        ):
            config = get_llm_config()
            kwargs = build_chat_openai_kwargs(config)
            assert kwargs == {
                "model": "test-model",
                "api_key": "test-key",
                "temperature": 0.2,
                "timeout": 15,
                "base_url": "https://test.example.com/v1",
            }
