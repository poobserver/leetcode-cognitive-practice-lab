from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from direct_html_workflow.workflow import (
    STRUCTURE_PROMPT,
    EXAMPLE_QUALITY_REQUIREMENTS,
    audit_page_plan,
    audit_direct_html,
    build_direct_prompt,
    build_page_plan_prompt,
    extract_json,
    generate_direct_html,
    normalize_problem,
    structure_problem_text,
    validate_problem_for_generation,
)


class WorkflowTests(unittest.TestCase):
    def test_extract_json_strips_markdown(self) -> None:
        data = extract_json('```json\n{"leetcodeId": 209, "titleEn": "Minimum Size Subarray Sum"}\n```')
        self.assertEqual(data["leetcodeId"], 209)

    def test_build_direct_prompt_injects_problem(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            prompt = Path(tmp) / "prompt.txt"
            prompt.write_text("题目：【在这里粘贴LeetCode题号、题名和题目描述】", encoding="utf-8")
            problem = normalize_problem({"leetcodeId": 209, "titleEn": "Minimum Size Subarray Sum"})
            result = build_direct_prompt(prompt, problem)
            self.assertIn("Minimum Size Subarray Sum", result)
            self.assertIn("迁移练习深度", result)
            self.assertIn("课程单元式交互实验室", result)

    def test_page_plan_prompt_uses_example_blueprint(self) -> None:
        problem = normalize_problem(
            {
                "leetcodeId": 209,
                "titleEn": "Minimum Size Subarray Sum",
                "description": "Given nums and target, find the minimum subarray length with sum at least target.",
                "examples": [{"input": "target=7, nums=[2,3,1,2,4,3]", "output": "2", "explanation": ""}],
                "constraints": ["1 <= nums.length <= 10^5"],
            }
        )
        prompt = build_page_plan_prompt(problem)
        self.assertIn("课程头部", prompt)
        self.assertIn("trace 播放器", prompt)
        self.assertIn("Minimum Size Subarray Sum", prompt)

    def test_page_plan_audit_rejects_shallow_plan(self) -> None:
        problem = normalize_problem({"leetcodeId": 0, "titleZh": "二分查找时间复杂度分析", "description": "分析二分查找代码的时间复杂度"})
        errors = audit_page_plan({"courseHeader": {"title": "x"}}, problem)
        self.assertTrue(any("stage" in error or "stageTrack" in error for error in errors))
        self.assertTrue(any("transferLearning" in error for error in errors))

    def test_structure_prompt_json_example_does_not_break_formatting(self) -> None:
        calls = []

        def fake_llm(prompt, **kwargs):
            calls.append(prompt)
            return {
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"leetcodeId": 209, "titleZh": "长度最小的子数组", '
                                '"titleEn": "Minimum Size Subarray Sum", "slug": '
                                '"minimum-size-subarray-sum", "description": '
                                '"Given a positive integer array and target, return the minimal length of a contiguous subarray whose sum is at least target.", '
                                '"examples": [{"input": "target = 7, nums = [2,3,1,2,4,3]", "output": "2", "explanation": "[4,3]"}], '
                                '"constraints": ["1 <= target <= 10^9", "1 <= nums.length <= 10^5"]}'
                            )
                        }
                    }
                ]
            }

        problem = structure_problem_text(
            "209. Minimum Size Subarray Sum\nExample 1...\nConstraints...",
            llm_call=fake_llm,
        )
        self.assertEqual(problem["leetcodeId"], 209)
        self.assertIn('"leetcodeId"', STRUCTURE_PROMPT)
        self.assertIn("209. Minimum Size Subarray Sum", calls[0])
        self.assertIn("迁移 trace", EXAMPLE_QUALITY_REQUIREMENTS)

    def test_validation_accepts_code_snippet_without_leetcode_metadata(self) -> None:
        problem = normalize_problem(
            {
                "leetcodeId": 0,
                "description": (
                    "下面函数实现了在一个升序整型数组arr中查找一个目标值target的位置，"
                    "请分析它的时间复杂度。\n"
                    "int search(int start, int end, int target, int *arr) { return -1; }"
                ),
                "functionSignature": "int search(int start, int end, int target, int *arr)",
            }
        )
        errors = validate_problem_for_generation(problem)
        self.assertEqual(errors, [])
        self.assertEqual(problem["titleZh"], "二分查找时间复杂度分析")

    def test_validation_rejects_vague_non_algorithm_text(self) -> None:
        problem = normalize_problem({"leetcodeId": 0, "description": "帮我生成一个页面"})
        errors = validate_problem_for_generation(problem)
        self.assertIn("题目描述过短，无法生成可靠学习材料", errors)

    def test_209_audit_rejects_shallow_transfer(self) -> None:
        problem = normalize_problem(
            {
                "leetcodeId": 209,
                "titleZh": "长度最小的子数组",
                "titleEn": "Minimum Size Subarray Sum",
                "slug": "minimum-size-subarray-sum",
            }
        )
        with tempfile.TemporaryDirectory() as tmp:
            html = Path(tmp) / "lesson.html"
            html.write_text(
                "<!doctype html><html><head><style></style></head><body>"
                "209 长度最小的子数组 Minimum Size Subarray Sum 迁移 参考答案 自动播放"
                "<script></script></body></html>",
                encoding="utf-8",
            )
            errors = audit_direct_html(html, problem)
            self.assertTrue(any("713" in error for error in errors))
            self.assertTrue(any("product" in error for error in errors))

    def test_generate_direct_html_writes_page_plan_first(self) -> None:
        problem = normalize_problem(
            {
                "leetcodeId": 0,
                "titleZh": "二分查找时间复杂度分析",
                "slug": "binary-search-complexity",
                "description": "下面函数在升序数组中用 mid 递归查找 target，请分析时间复杂度。",
                "functionSignature": "int search(int start, int end, int target, int *arr)",
            }
        )
        plan = {
            "courseHeader": {
                "sourceLabel": "代码分析题",
                "title": "二分查找时间复杂度分析",
                "difficultyOrType": "复杂度分析",
                "tags": ["二分查找", "递归"],
                "skillThesis": "用区间减半理解 O(log n)",
            },
            "stageTrack": [
                {"id": "stage-1", "title": "读代码", "learnerTask": "标出 low/high/mid", "unlockAction": "check"},
                {"id": "stage-2", "title": "看一次递归", "learnerTask": "预测下一段区间", "unlockAction": "next"},
                {"id": "stage-3", "title": "状态变量", "learnerTask": "填写剩余规模", "unlockAction": "check"},
                {"id": "stage-4", "title": "复杂度", "learnerTask": "选择递推式", "unlockAction": "check"},
                {"id": "stage-5", "title": "迁移", "learnerTask": "改成迭代二分", "unlockAction": "play"},
            ],
            "algorithmWorkspace": {
                "visualPanel": "升序数组、low/high/mid、丢弃区间",
                "explanationPanel": "每次比较后只保留一半",
                "stateStrip": ["low", "high", "mid", "remainingSize"],
            },
            "tracePlayer": {
                "traceStateFields": ["call", "low", "high", "mid", "remainingSize", "caption"],
                "renderTargets": ["array", "code", "state", "caption"],
                "minimumFrames": 6,
                "controls": ["prev", "next", "play", "reset"],
            },
            "codePractice": {
                "slots": [
                    {"id": "slot-1", "prompt": "mid 公式", "options": ["start + (end-start)/2"], "answer": "start + (end-start)/2", "feedback": "避免溢出"},
                    {"id": "slot-2", "prompt": "右半递归", "options": ["mid+1"], "answer": "mid+1", "feedback": "丢弃左半"},
                    {"id": "slot-3", "prompt": "复杂度", "options": ["O(log n)"], "answer": "O(log n)", "feedback": "每次减半"},
                ]
            },
            "transferLearning": {
                "transferProblem": {"sourceLabel": "变体", "title": "迭代二分 lower_bound", "description": "寻找第一个大于等于 target 的位置"},
                "preservedConcepts": ["有序性", "区间", "mid"],
                "changedConcepts": ["递归改循环", "返回插入点", "边界收敛"],
                "scaffoldSlots": [
                    {"id": "transfer-slot-1", "prompt": "循环条件", "answer": "left < right"},
                    {"id": "transfer-slot-2", "prompt": "mid", "answer": "(left+right)//2"},
                    {"id": "transfer-slot-3", "prompt": "收缩右边界", "answer": "right = mid"},
                    {"id": "transfer-slot-4", "prompt": "收缩左边界", "answer": "left = mid + 1"},
                ],
                "transferTrace": {
                    "stateFields": ["left", "right", "mid", "decision", "caption"],
                    "minimumFrames": 6,
                    "controls": ["prev", "next", "play", "reset"],
                },
                "proofObligation": "证明区间始终包含第一个可行位置",
            },
            "visualStyle": {"layout": "course-lab", "desktop": "two-column", "mobile": "single-column"},
        }
        html = "<!doctype html><html><head><style></style></head><body>二分查找时间复杂度分析 迁移 参考答案 自动播放<script></script></body></html>"
        calls = []

        def fake_llm(prompt, **kwargs):
            calls.append(kwargs.get("system"))
            if kwargs.get("json_output"):
                return {"choices": [{"finish_reason": "stop", "message": {"content": __import__("json").dumps(plan, ensure_ascii=False)}}], "usage": {"completion_tokens": 100}}
            return {"choices": [{"finish_reason": "stop", "message": {"content": html}}], "usage": {"completion_tokens": 50}}

        with tempfile.TemporaryDirectory() as tmp:
            prompt = Path(tmp) / "prompt.txt"
            prompt.write_text("题目：【在这里粘贴LeetCode题号、题名和题目描述】", encoding="utf-8")
            result = generate_direct_html(problem, prompt_path=prompt, output_dir=Path(tmp) / "out", llm_call=fake_llm)
            self.assertTrue(result.page_plan_json.exists())
            self.assertTrue(result.output.exists())
            self.assertEqual(result.report["pagePlanStatus"], "passed")
            self.assertIn("page_plan", result.report["pagePlanJson"])


if __name__ == "__main__":
    unittest.main()
