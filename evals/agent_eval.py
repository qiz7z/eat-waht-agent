"""Agent 行为评测脚本。

运行：
    python evals/agent_eval.py

说明：
- 默认使用无 API Key 的 fallback / 本地流程能力，不依赖真实大模型。
- 评测重点是 Agent MVP 的关键行为：可响应、可重置、可保留历史。
"""

from dataclasses import dataclass
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.agent import MealRecommenderAgent  # noqa: E402


@dataclass
class EvalCase:
    name: str
    inputs: list[str]
    expected_keywords: list[str]


EVAL_CASES = [
    EvalCase(
        name="fallback_without_api_key",
        inputs=["想吃辣的"],
        expected_keywords=["API Key", "麻辣烫"],
    ),
    EvalCase(
        name="reset_conversation",
        inputs=["想吃辣的", "重新开始"],
        expected_keywords=["麻辣烫"],
    ),
]


def run_case(case: EvalCase) -> tuple[bool, str]:
    agent = MealRecommenderAgent(api_key="")
    last_response = ""
    for text in case.inputs:
        last_response = agent.invoke(text)

    missing = [keyword for keyword in case.expected_keywords if keyword not in last_response]
    if missing:
        return False, f"missing keywords: {missing}; response={last_response!r}"
    return True, "passed"


def main() -> int:
    passed = 0
    failed = 0

    print("Agent Eval Results")
    print("==================")

    for case in EVAL_CASES:
        ok, message = run_case(case)
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {case.name}: {message}")
        if ok:
            passed += 1
        else:
            failed += 1

    print("==================")
    print(f"passed={passed} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
