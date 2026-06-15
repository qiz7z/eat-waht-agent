.PHONY: install test lint run-api run-gradio docker-build docker-up eval clean help

help:  ## 显示帮助
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

install:  ## 安装依赖
	pip install -r requirements.txt

test:  ## 运行测试
	pytest tests/ -v --tb=short

test-cov:  ## 运行测试并生成覆盖率报告
	pytest tests/ -v --cov=agent --cov-report=term-missing

lint:  ## 检查代码风格（可选）
	python -m py_compile api.py
	python -m py_compile app.py
	python -c "from agent.agent import MealRecommenderAgent; print('import ok')"

run-api:  ## 启动 FastAPI 服务
	python api.py

run-gradio:  ## 启动 Gradio 界面
	python app.py

eval:  ## 运行 Agent 行为评测
	python evals/agent_eval.py

docker-build:  ## 构建 Docker 镜像
	docker build -t eat-what-agent .

docker-up:  ## 启动 Docker 服务（仅 API）
	docker compose up -d

docker-up-all:  ## 启动 Docker 服务（含 Gradio）
	docker compose --profile gradio up -d

docker-down:  ## 停止 Docker 服务
	docker compose down

clean:  ## 清理缓存
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf .coverage htmlcov/
