# 🍽️ 吃什么推荐助手

一个面向中国大学生的智能餐饮推荐 Web 应用，通过多轮对话了解你的偏好，综合考虑时间、天气、心情、预算、健康需求等因素，帮你挑顿合胃口的！

## 特性

- **Tool Calling Agent**：基于 LangChain Tool Calling，支持多工具协作
- **智能追问**：像朋友一样聊天，逐步了解你的口味和需求
- **全维度推荐**：综合考虑口味、预算、天气、心情、健康、社交场景等因素
- **追问式策略**：1 个主要推荐 + 2 个备选方案，不满意可以再选
- **本地食物数据库**：内置 75+ 种常见中式食物，支持按口味、预算、类别搜索
- **食物排行榜**：实时热门食物排行榜，一键获取推荐
- **数据爬虫**：支持从美食杰等网站自动爬取更新食物数据
- **会话隔离**：每个用户会话拥有独立偏好状态，避免串话
- **会话生命周期管理**：支持 TTL 自动过期和最大会话数限制
- **统一模型配置**：集中管理 `api_key`、`model`、`base_url`、温度和超时
- **标准 API**：提供 FastAPI `/chat`、`/reset`、`/health`、`/food_rankings`、`/search_food` 等接口
- **运行日志**：记录 Agent 调用、工具调用和异常信息（支持脱敏）
- **行为评测**：提供轻量 eval 脚本验证关键 Agent 行为
- **Docker 部署**：提供 Dockerfile 和 docker-compose 一键部署
- **Web 界面**：提供 Vue 3 + TypeScript 前端，支持多轮对话和食物排行榜
- **本地运行**：支持本地部署，保护隐私

## Agent 架构设计

### 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         用户层 (User Layer)                      │
│  ┌──────────────┐  ┌──────────────────────────────────────────┐  │
│  │ Vue 3 前端   │  │  第三方调用 / cURL                       │  │
│  │ (frontend/)  │  │                                          │  │
│  └──────┬───────┘  └─────────────────────┬────────────────────┘  │
└─────────┼─────────────────┼─────────────────────┼───────────────┘
          │                 │                     │
          ▼                 ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                       服务层 (Service Layer)                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              FastAPI (api.py)                            │  │
│  │  /chat  /reset  /health  /sessions/{id}                 │  │
│  │  ┌─────────────────┐  ┌─────────────────────────────┐  │  │
│  │  │ Session Manager  │  │  会话 TTL 自动清理           │  │  │
│  │  │ (per-session)    │  │  MAX_SESSIONS 限制          │  │  │
│  │  └────────┬────────┘  └─────────────────────────────┘  │  │
│  └───────────┼──────────────────────────────────────────────┘  │
└──────────────┼──────────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Agent 核心层 (Core Layer)                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │           MealRecommenderAgent (agent.py)                │  │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │              LangChain Tool Calling Agent           │  │  │
│  │  │  ┌─────────────┐  ┌────────────────────────────┐  │  │  │
│  │  │  │ SYSTEM_PROMPT│  │     ChatOpenAI (LLM)      │  │  │  │
│  │  │  │ 角色/语气/   │  │  ┌─────────────────────┐  │  │  │  │
│  │  │  │ 工作流定义   │  │  │  agent/config.py    │  │  │  │  │
│  │  │  └─────────────┘  │  │  统一模型配置管理    │  │  │  │  │
│  │  │                   │  └─────────────────────┘  │  │  │  │
│  │  │                   └────────────────────────────┘  │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                               │                                │
│                               ▼                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    Tools 层 (tools.py)                    │  │
│  │  ┌────────────┐ ┌────────────┐ ┌──────────────────────┐ │  │
│  │  │save_pref.  │ │get_pref.   │ │  get_context_info    │ │  │
│  │  │保存偏好    │ │获取偏好    │ │  获取时间/天气       │ │  │
│  │  └────────────┘ └────────────┘ └──────────────────────┘ │  │
│  │  ┌────────────┐ ┌────────────────────────────────────┐ │  │
│  │  │reset_pref. │ │  generate_recommendation           │ │  │
│  │  │重置偏好    │ │  生成推荐（本地规则 + LLM 增强）   │ │  │
│  │  └────────────┘ └────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────┘  │
│                               │                                │
│                               ▼                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │               状态管理层 (State Layer)                    │  │
│  │  ┌─────────────────────┐  ┌────────────────────────────┐│  │
│  │  │  SessionStateManager │  │    ContextVar 隔离         ││  │
│  │  │  per-agent 状态      │  │    线程/协程安全           ││  │
│  │  └─────────────────────┘  └────────────────────────────┘│  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      基础设施层 (Infra Layer)                    │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌─────────────┐ │
│  │  日志系统   │  │  配置管理  │  │  Docker    │  │  测试/评测  │ │
│  │  logging   │  │  .env      │  │  部署      │  │  pytest/eval│ │
│  └────────────┘ └────────────┘ └────────────┘ └─────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Agent 工作流程图

```
用户输入
   │
   ▼
┌──────────────┐     ┌──────────────────────────────────────┐
│  接收消息     │────▶│         MealRecommenderAgent          │
└──────────────┘     └─────────────────┬────────────────────┘
                                       │
                         ┌─────────────┴─────────────┐
                         │  是否有 API Key / LLM 就绪？│
                         └─────────────┬─────────────┘
                              ┌────────┴────────┐
                              ▼                 ▼
                       ┌──────────┐       ┌──────────┐
                       │  ✅ 是   │       │  ❌ 否   │
                       └────┬─────┘       └────┬─────┘
                            │                  │
                            ▼                  ▼
                   ┌────────────────┐   ┌────────────────┐
                   │ LangChain Agent│   │ Fallback 响应  │
                   │ Tool Calling   │   │ 本地推荐兜底   │
                   └───────┬────────┘   └────────────────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌────────────┐  ┌────────────┐  ┌────────────────┐
    │ get_context│  │save/get    │  │  generate_     │
    │ _info      │  │_preference │  │  recommendation│
    │ 获取上下文 │  │ 偏好读写   │  │  生成推荐      │
    └────────────┘  └────────────┘  └────────────────┘
                           │
                           ▼
                   ┌────────────────┐
                   │  返回响应给用户 │
                   │  更新对话历史   │
                   └────────────────┘
```

## Agent 构建流程

本项目遵循以下 Agent 构建流程，覆盖从需求到部署的完整生命周期：

```
┌─────────────────────────────────────────────────────────────────┐
│                    Agent 构建流程 (Build Pipeline)                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ① 需求定义          ② 角色设计          ③ 工具设计             │
│  ┌──────────┐       ┌──────────┐       ┌──────────┐            │
│  │ 场景分析  │──────▶│ SYSTEM_  │──────▶│ 定义工具 │            │
│  │ 用户画像  │       │ PROMPT   │       │ 参数/返回│            │
│  │ 核心功能  │       │ 角色/语气 │       │ 异常处理 │            │
│  └──────────┘       └──────────┘       └──────────┘            │
│       │                   │                   │                 │
│       ▼                   ▼                   ▼                 │
│  ④ 模型配置          ⑤ 状态管理          ⑥ Agent 编排          │
│  ┌──────────┐       ┌──────────┐       ┌──────────┐            │
│  │ config.py│──────▶│ Session  │──────▶│ LangChain│            │
│  │ 统一配置  │       │ State    │       │ Agent    │            │
│  │ 多模型兼容│       │ 隔离     │       │ Tool Call│            │
│  └──────────┘       └──────────┘       └──────────┘            │
│       │                   │                   │                 │
│       ▼                   ▼                   ▼                 │
│  ⑦ 服务化             ⑧ 前端交互          ⑨ 观测日志           │
│  ┌──────────┐       ┌──────────┐       ┌──────────┐            │
│  │ FastAPI  │──────▶│ Vue 3    │──────▶│ 结构化   │            │
│  │ REST API │       │ TypeScript│      │ 日志记录 │            │
│  │ 会话管理 │       │ 聊天交互 │       │ 链路追踪 │            │
│  └──────────┘       └──────────┘       └──────────┘            │
│       │                   │                   │                 │
│       ▼                   ▼                   ▼                 │
│  ⑩ 测试保障          ⑪ 行为评测          ⑫ 部署上线            │
│  ┌──────────┐       ┌──────────┐       ┌──────────┐            │
│  │ 单元测试  │──────▶│ eval 脚本│──────▶│ Docker   │            │
│  │ 75+ 用例  │       │ 场景覆盖 │       │ 一键部署 │            │
│  │ 覆盖率   │       │ 行为验证 │       │ compose  │            │
│  └──────────┘       └──────────┘       └──────────┘            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 各阶段说明

| 阶段 | 产出 | 对应文件 |
|------|------|----------|
| ① 需求定义 | 场景、用户画像、功能列表 | `README.md` |
| ② 角色设计 | SYSTEM_PROMPT、语气、工作流 | `agent/agent.py` |
| ③ 工具设计 | 工具函数、参数定义、返回格式 | `agent/tools.py` |
| ④ 模型配置 | 统一配置、多模型兼容 | `agent/config.py` |
| ⑤ 状态管理 | 会话隔离、ContextVar | `agent/tools.py` |
| ⑥ Agent 编排 | LangChain Agent、Tool Calling | `agent/agent.py` |
| ⑦ 服务化 | REST API、会话管理、TTL | `api.py` |
| ⑧ 前端交互 | Vue 3 + TypeScript 前端 | `frontend/` |
| ⑨ 观测日志 | 结构化日志、调用链路 | `agent/logging_config.py` |
| ⑩ 测试保障 | 单元测试、边界覆盖 | `tests/` |
| ⑪ 行为评测 | 场景评测、行为验证 | `evals/agent_eval.py` |
| ⑫ 部署上线 | Docker、Compose | `Dockerfile`, `docker-compose.yml` |

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

### 3. 启动 FastAPI 服务

```bash
python api.py
# 或
make run-api
```

API 地址：`http://localhost:8000`

常用接口：

```bash
# 健康检查
curl http://localhost:8000/health

# 聊天
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"想吃辣的，预算 30 元以内\"}"

# 重置会话
curl -X POST http://localhost:8000/reset \
  -H "Content-Type: application/json" \
  -d "{\"session_id\":\"你的 session_id\"}"

# 获取食物排行榜
curl http://localhost:8000/food_rankings?limit=10

# 搜索食物
curl -X POST http://localhost:8000/search_food \
  -H "Content-Type: application/json" \
  -d "{\"taste\":\"辣\", \"budget\":\"20-30元\"}"

# 获取食物统计
curl http://localhost:8000/food_stats
```

### 4. 启动 Vue 前端（可选）

```bash
cd frontend
npm install
npm run dev
```

然后在浏览器中访问：`http://localhost:3000`

前端通过 Vite 代理自动转发 `/api/*` 请求到 FastAPI 后端。

### 5. Docker 部署（可选）

```bash
# 仅启动 API 服务
docker compose up -d

# 同时启动 API + 前端
docker compose up -d
```

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
eat-what-agent/
├── api.py                    # FastAPI 标准接口入口（含会话 TTL 管理）
├── agent/                    # Agent 核心模块
│   ├── __init__.py
│   ├── agent.py              # LangChain Tool Calling Agent 主类
│   ├── config.py             # 大模型统一配置
│   ├── logging_config.py     # 日志配置（线程安全）
│   ├── models.py             # 数据模型
│   ├── tools.py              # LangChain 工具定义（10个工具）
│   ├── food_data_manager.py  # 食物数据库管理器
│   └── crawler.py            # 食物数据爬虫
├── data/                     # 数据目录
│   └── food_database.json    # 食物数据库（75+种食物）
├── frontend/                 # Vue 3 + TypeScript 前端
│   ├── src/
│   │   ├── App.vue           # 主界面（含食物排行榜）
│   │   ├── api.ts            # API 客户端
│   │   └── components/
│   │       ├── ChatMessage.vue     # 聊天气泡组件
│   │       └── TypingIndicator.vue # 打字指示器
│   ├── vite.config.ts        # Vite 代理配置
│   └── package.json
├── static/                   # 前端构建输出
├── tests/                    # 单元测试（47个用例）
│   ├── test_agent.py
│   ├── test_api.py           # FastAPI 接口测试
│   ├── test_config.py
│   ├── test_models.py
│   └── test_tools.py
├── evals/                    # Agent 行为评测
│   └── agent_eval.py
├── Dockerfile                # Docker 镜像定义
├── docker-compose.yml        # Docker Compose 编排
├── Makefile                  # 常用开发命令
├── requirements.txt          # Python 依赖
├── .env.example              # 环境变量模板
├── PROJECT_ANALYSIS.md       # 项目深度分析报告
├── FIX_REPORT.md             # 问题修复报告
└── README.md                 # 项目说明
```

## 技术栈

- **Python 3.11+**
- **LangChain 1.3.9** - 大语言模型框架
- **FastAPI** - 标准 API 服务
- **Vue 3 + TypeScript** - 前端框架
- **Vite** - 前端构建工具
- **Pydantic** - 数据验证
- **BeautifulSoup4** - 网页爬虫
- **Docker** - 容器化部署

## 开发

### 常用命令（Make）

```bash
make help          # 查看所有命令
make install       # 安装依赖
make test          # 运行测试
make test-cov      # 运行测试 + 覆盖率
make run-api       # 启动 API 服务
make run-frontend  # 启动 Vue 前端
make eval          # 运行评测
make docker-build  # 构建镜像
make docker-up     # 启动容器
```

### 运行测试

```bash
pytest tests/ -v
# 或
make test
```

### 运行 Agent 行为评测

```bash
python evals/agent_eval.py
# 或
make eval
```

### 查看日志

默认日志文件：

```text
logs/agent.log
```

可在 `.env` 中调整：

```env
LOG_LEVEL=INFO
LOG_DIR=logs
LOG_FILE=agent.log
```

### 环境变量参考

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `LLM_API_KEY` | 大模型 API Key | - |
| `LLM_MODEL` | 模型名称 | `gpt-4o-mini` |
| `LLM_BASE_URL` | API Base URL | - |
| `LLM_TEMPERATURE` | 温度 | `0.7` |
| `LLM_TIMEOUT` | 超时（秒） | `15` |
| `SESSION_TTL_SECONDS` | 会话过期时间（秒） | `3600` |
| `MAX_SESSIONS` | 最大同时活跃会话数 | `200` |
| `CORS_ALLOW_ORIGINS` | CORS 允许的来源，逗号分隔 | `*` |
| `CORS_ALLOW_METHODS` | CORS 允许的方法，逗号分隔 | `GET,POST,DELETE,OPTIONS` |
| `CORS_ALLOW_HEADERS` | CORS 允许的头部，逗号分隔 | `*` |
| `LOG_LEVEL` | 日志级别 | `INFO` |
| `LOG_DIR` | 日志目录 | `logs` |
| `LOG_FILE` | 日志文件名 | `agent.log` |

## Agent 开发流程覆盖

本项目覆盖了一个 Agent MVP 的主要开发环节：

1. **角色定义**：`SYSTEM_PROMPT` 定义助手角色、语气和任务流程
2. **工具设计**：`agent/tools.py` 提供 10 个工具（上下文、偏好、推荐、食物数据库等）
3. **状态管理**：`SessionStateManager` 隔离多用户会话状态
4. **模型配置**：`agent/config.py` 统一管理 OpenAI-compatible 模型接入
5. **数据管理**：`agent/food_data_manager.py` 管理 75+ 种食物的本地数据库
6. **数据采集**：`agent/crawler.py` 支持从公开网站爬取食物数据
7. **交互入口**：`frontend/` 提供 Vue 3 聊天界面和食物排行榜，`api.py` 提供标准 API
8. **观测能力**：`agent/logging_config.py` 记录运行链路与异常（支持脱敏）
9. **质量保障**：`tests/` 提供 47 个单元测试，`evals/` 提供 Agent 行为评测
10. **降级策略**：无 API Key 或模型失败时返回本地推荐兜底

## License

MIT
