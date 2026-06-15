# 🍽️ 吃什么推荐助手

一个面向中国大学生的智能餐饮推荐 Web 应用，通过多轮对话了解你的偏好，综合考虑时间、天气、心情、预算、健康需求等因素，帮你挑顿合胃口的！

## 特性

- **智能追问**：像朋友一样聊天，逐步了解你的口味和需求
- **全维度推荐**：综合考虑口味、预算、天气、心情、健康、社交场景等因素
- **追问式策略**：1 个主要推荐 + 2 个备选方案，不满意可以再选
- **Web 界面**：简洁的聊天界面，支持移动端
- **本地运行**：支持本地部署，保护隐私

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量（可选）

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置你的大模型 API Key、模型和 Base URL。

项目已将模型配置统一放在 `agent/config.py` 中，支持 OpenAI 以及兼容 OpenAI API 的服务（DeepSeek、Kimi、智谱、通义千问兼容模式、LM Studio、Ollama 等）。

```env
# 推荐使用：通用 OpenAI-Compatible 配置
LLM_PROVIDER=openai
LLM_API_KEY=your_api_key_here
LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=
LLM_TEMPERATURE=0.7
LLM_TIMEOUT=15

# DeepSeek 示例
# OPENAI_API_KEY=your_deepseek_key_here
# OPENAI_MODEL=deepseek-chat
# OPENAI_BASE_URL=https://api.deepseek.com

# 通义千问兼容模式示例
# DASHSCOPE_API_KEY=your_dashscope_key_here
# DASHSCOPE_MODEL=qwen-turbo
# DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

配置优先级：显式传参 > `LLM_*` > `OPENAI_*` > `DASHSCOPE_*` > 默认值。

### 3. 启动应用

```bash
python3 app.py
```

然后在浏览器中访问：`http://localhost:7860`

## 使用指南

1. 打开应用，Agent 会自动开始对话
2. 回答 Agent 的问题，告诉它你想吃什么
3. Agent 会根据你的偏好生成推荐
4. 如果不满意，可以看看备选方案，或输入"重新开始"再来一轮

### 对话示例

```
你：想吃辣的
Agent：今天预算多少？
你：30 块左右
Agent：现在心情怎么样？这顿想犒劳自己还是随便吃？
你：随便吃吧
...
Agent：为你生成推荐...
```

## 项目结构

```
meal-recommender/
├── app.py               # Gradio Web UI 入口
├── agent/               # Agent 核心模块
│   ├── __init__.py
│   ├── models.py        # 数据模型
│   ├── context.py       # 上下文服务（时间、天气）
│   ├── preference.py    # 偏好收集器
│   ├── recommendation.py # 推荐引擎
│   └── controller.py    # Agent 控制器
├── tests/               # 单元测试
│   ├── test_models.py
│   ├── test_context.py
│   ├── test_preference.py
│   └── test_controller.py
├── requirements.txt     # Python 依赖
├── .env.example         # 环境变量模板
└── README.md            # 项目说明
```

## 技术栈

- **Python 3.11+**
- **LangChain** - 大语言模型框架
- **Gradio** - Web UI 框架
- **Pydantic** - 数据验证

## 开发

### 运行测试

```bash
pytest tests/ -v
```

## License

MIT
