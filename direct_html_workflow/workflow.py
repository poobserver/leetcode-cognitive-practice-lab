from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .llm import DEFAULT_MODEL, chat_completion, first_message_text


STRUCTURE_SYSTEM = (
    "你是算法题目结构化助手。只输出 JSON，不输出 Markdown。"
    "必须忠实保留用户粘贴的题面信息；可以推断简短标题和标签，但不要改题。"
)


DIRECT_HTML_SYSTEM = (
    "你是一个只输出完整 standalone HTML 文件的资深算法交互课件生成器。"
    "不要输出 Markdown，不要输出解释，只输出 HTML。"
)


PAGE_PLAN_SYSTEM = (
    "你是算法交互课件 page_plan 架构师。只输出 JSON，不输出 Markdown。"
    "page_plan 必须可直接指导后续 HTML 生成。"
)


EXAMPLE_BLUEPRINT = """

## example 目录抽取出的结构蓝图（few-shot 摘要，不是全文）

高质量页面共同结构：

1. 课程头部 courseHeader
   - sourceLabel: LeetCode 题号或普通算法题来源
   - title: 题名或分析主题
   - difficultyOrType: 难度或题型
   - tags: 2-6 个算法标签
   - skillThesis: 本课训练的核心认知能力

2. 阶段轨道 stageTrack
   - 5-7 个阶段
   - 每个阶段有 id、title、learnerTask、unlockAction
   - 阶段不是长文目录，而是可操作学习路径

3. 算法工作区 algorithmWorkspace
   - 左侧/上方为 visualPanel：数组、字符串、指针、窗口、递归区间、矩阵或调用栈
   - 右侧/下方为 explanationPanel：当前决策、为什么安全、下一步预测
   - 必须有 metrics/state strip，例如 left/right/sum/best/mid/low/high/count/depth

4. trace 播放器 tracePlayer
   - traceStateFields: 逐帧状态字段
   - renderTargets: 状态要绑定到哪些 UI 区域
   - controls: prev/next/play/reset
   - 至少 6 帧，帧必须体现算法状态变化

5. 代码槽位 codePractice
   - 至少 3 个 slot
   - 每个 slot 有 prompt、options、answer、feedback
   - 必须有检查、参考答案、一键填入或等价操作

6. 迁移学习 transferLearning
   - transferProblem: 明确迁移题或同主题变体
   - preservedConcepts: 至少 3 个
   - changedConcepts: 至少 3 个
   - scaffoldSlots: 至少 4 个
   - transferTrace: 至少 6 帧
   - proofObligation: 迁移后新增证明义务

参考单元模式：

- #167 Two Sum II:
  - skillThesis: 利用排序单调性安全排除端点
  - stateFields: line,l,r,ex,ans,caption
  - renderTargets: code_highlight,array_endpoints,current_sum,candidate_pair_matrix,metrics
  - migration: #2824 Count Pairs，变化为批量统计 right-left

- #209 Minimum Size Subarray Sum:
  - skillThesis: 满足条件后持续收缩以寻找最短窗口
  - stateFields: line,l,r,sum,best,valid,bestCells,caption
  - renderTargets: code_highlight,window_boundaries,current_sum,valid_state,best_length,metrics
  - migration: #713 Product Less Than K，sum 迁移为 product，最短长度迁移为计数 right-left+1

- 普通代码分析题，例如二分查找时间复杂度：
  - skillThesis: 用递归区间每次减半解释 O(log n)
  - visualPanel: sorted array + low/high/mid + discarded half + recursion depth
  - stateFields: call,low,high,mid,comparison,remainingSize,depth,caption
  - transfer: 迁移到迭代二分、lower_bound 或递归树复杂度分析
"""


MIGRATION_DEPTH_REQUIREMENTS = """

## 额外硬性要求：迁移练习深度

迁移练习不得只包含一个选择题、一个 textarea 或一个简单变体。
迁移练习必须是一个小型交互实验，并且至少包含以下 5 个部分：

1. 迁移题原题阅读
   - 显示迁移题题号（若有）、题名、题意、示例或测试输入。
   - 至少 2 个读题检查问题。

2. 原题与迁移题对照
   - 明确列出至少 3 个“保留点”。
   - 明确列出至少 3 个“变化点”。
   - 用户必须通过点击、勾选或选择来确认这些保留/变化点。

3. 迁移算法拼装
   - 不允许只给自由输入框。
   - 至少 4 个代码槽位或选项组。
   - 每个槽位必须有检查、错误反馈和参考答案。

4. 迁移样例逐帧动画
   - 必须有 transferTrace 或等价迁移轨迹数组。
   - 至少 6 帧。
   - 每帧展示 left/right/windowState/answer/currentDecision 或同等字段。
   - 必须有上一步、下一步、自动播放、重置。

5. 迁移总结
   - 总结原题 skill 如何迁移。
   - 明确说明新证明义务。

对于 LeetCode 209，迁移题必须使用 LeetCode 713 Subarray Product Less Than K / 乘积小于 K 的子数组。
页面必须包含 product、k、right-left+1 或 right - left + 1，并解释为什么固定 right 时可以批量计数。
不要把迁移题简化成“总和小于 target 的连续子数组个数”。

如果原题不是 LeetCode 题，而是普通算法题、代码分析题、考试题或面试题：
- 不要编造 LeetCode 题号。
- 迁移练习可以选择一个同主题变体，不强制是 LeetCode。
- 迁移题必须仍然有明确题意、互动练习、逐帧动画和总结。
"""


EXAMPLE_QUALITY_REQUIREMENTS = """

## 额外硬性要求：对齐 example 目录的课程页质量

生成的 HTML 不得只是普通文章或题解页，必须是“课程单元式交互实验室”：

1. 首屏结构
   - 必须有课程单元标题区，显示来源/题号（若有）、题名、难度或题型、标签。
   - 必须有一句核心 skill thesis，说明本题训练的算法认知能力。
   - 必须显示原题描述、示例/测试输入（若有）、约束（若有）、函数签名或核心代码（若有）。

2. 学习路径
   - 必须有 5 到 7 个阶段或步骤导航。
   - 每个阶段必须有明确任务，不允许只有长段解释。
   - 阶段之间必须通过按钮、选择、检查或播放控件推进。

3. 动画和状态面板
   - 必须有数组/字符串/图结构的可视化区域。
   - 必须展示关键状态变量，例如 left/right/window_sum/product/count/best/mid 等。
   - 必须有逐帧 trace 数据数组或等价结构。
   - 必须有上一步、下一步、自动播放、重置。

4. 代码联动
   - 必须有代码高亮或逐行 trace。
   - 必须有至少 3 个代码槽位、选择题或拼装题。
   - 每个练习必须有检查、错误反馈、参考答案或一键填入。

5. 迁移学习
   - LeetCode 原题优先迁移到明确题号和题名的相关 LeetCode 题。
   - 普通算法题可以迁移到同主题变体或改造练习，不要强行编造 LeetCode 题号。
   - 必须包含原题/迁移题对照、保留点、变化点、迁移算法拼装、迁移 trace、迁移总结。
   - 迁移练习必须比普通总结更深，用户需要实际操作。

6. 视觉质量
   - 不要把内容塞成一张大卡片。
   - 使用清晰的左右工作区、阶段导航、状态条、可视化面板和练习面板。
   - 桌面宽屏下首屏应像一个可操作实验室，不像静态文档。
   - 移动端必须单列可读，文字不能溢出按钮或卡片。
"""


STRUCTURE_PROMPT = """
请把用户粘贴的算法题、LeetCode 题、代码分析题或面试题文本结构化为下面 JSON 形状。

硬性要求：
- 只输出 JSON。
- 如果题面没有 LeetCode 题号，leetcodeId 设为 0。
- 如果题面没有明确标题，请根据题干推断一个简短 titleZh，例如“二分查找时间复杂度分析”。
- 如果题面没有英文标题，titleEn 可为空字符串。
- examples 必须是数组，每个元素包含 input、output、explanation；没有示例则返回空数组。
- constraints 必须是字符串数组；没有约束则返回空数组。
- tags 可根据题目内容推断，但不要超过 8 个。
- slug 使用英文题名或主题的小写短横线形式；如果无法确定，用 algorithm-question。

JSON 形状：
{
  "leetcodeId": 0,
  "titleZh": "",
  "titleEn": "",
  "slug": "",
  "difficulty": "",
  "tags": [],
  "description": "",
  "examples": [
    {"input": "", "output": "", "explanation": ""}
  ],
  "constraints": [],
  "functionSignature": ""
}

用户粘贴的题目文本：

---
__PROBLEM_TEXT__
---
"""


PAGE_PLAN_PROMPT = """
请基于题目 JSON 和 example 结构蓝图，生成 page_plan.json。

硬性要求：
- 只输出 JSON。
- 不要输出 HTML。
- 不要编造 LeetCode 题号；如果原题不是 LeetCode，sourceLabel 使用“普通算法题”或“代码分析题”。
- page_plan 必须包含课程头部、阶段轨道、算法工作区、状态变量条、trace 播放器、代码槽位、迁移题阅读、迁移对照、迁移 scaffold、迁移 trace。
- 所有阶段、slot、trace 字段必须贴合本题算法，不要使用通用空话。

JSON 形状：
{
  "courseHeader": {
    "sourceLabel": "",
    "title": "",
    "difficultyOrType": "",
    "tags": [],
    "skillThesis": ""
  },
  "stageTrack": [
    {"id": "stage-1", "title": "", "learnerTask": "", "unlockAction": ""}
  ],
  "algorithmWorkspace": {
    "visualPanel": "",
    "explanationPanel": "",
    "stateStrip": []
  },
  "tracePlayer": {
    "traceStateFields": [],
    "renderTargets": [],
    "minimumFrames": 6,
    "controls": ["prev", "next", "play", "reset"]
  },
  "codePractice": {
    "slots": [
      {"id": "slot-1", "prompt": "", "options": [], "answer": "", "feedback": ""}
    ]
  },
  "transferLearning": {
    "transferProblem": {"sourceLabel": "", "title": "", "description": ""},
    "preservedConcepts": [],
    "changedConcepts": [],
    "scaffoldSlots": [
      {"id": "transfer-slot-1", "prompt": "", "answer": ""}
    ],
    "transferTrace": {
      "stateFields": [],
      "minimumFrames": 6,
      "controls": ["prev", "next", "play", "reset"]
    },
    "proofObligation": ""
  },
  "visualStyle": {
    "layout": "course-lab",
    "desktop": "",
    "mobile": ""
  }
}

题目 JSON：

__PROBLEM_JSON__

结构蓝图：

__EXAMPLE_BLUEPRINT__
"""


@dataclass
class DirectHtmlResult:
    output: Path
    problem_json: Path
    page_plan_json: Path
    report: Dict[str, Any]
    audit_errors: List[str]


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def extract_json(text: str) -> Dict[str, Any]:
    content = text.strip()
    if content.startswith("```"):
        content = "\n".join(line for line in content.splitlines() if not line.strip().startswith("```")).strip()
    start = content.find("{")
    end = content.rfind("}")
    if start < 0 or end < start:
        raise ValueError("LLM response does not contain a JSON object")
    return json.loads(content[start : end + 1])


def normalize_problem(problem: Dict[str, Any], fallback_text: str = "") -> Dict[str, Any]:
    fallback_title = infer_title(problem, fallback_text)
    normalized: Dict[str, Any] = {
        "leetcodeId": int(problem.get("leetcodeId") or 0),
        "titleZh": str(problem.get("titleZh") or fallback_title),
        "titleEn": str(problem.get("titleEn") or ""),
        "slug": str(problem.get("slug") or fallback_title or "algorithm-question"),
        "difficulty": str(problem.get("difficulty") or ""),
        "tags": list(problem.get("tags") or []),
        "description": str(problem.get("description") or fallback_text),
        "examples": list(problem.get("examples") or []),
        "constraints": list(problem.get("constraints") or []),
        "functionSignature": str(problem.get("functionSignature") or ""),
    }
    if not normalized["slug"]:
        normalized["slug"] = "algorithm-question"
    normalized["slug"] = re.sub(r"[^a-z0-9-]+", "-", normalized["slug"].lower().replace("_", "-")).strip("-")
    if not normalized["slug"]:
        normalized["slug"] = "algorithm-question"
    return normalized


def infer_title(problem: Dict[str, Any], fallback_text: str = "") -> str:
    for key in ("titleZh", "titleEn"):
        title = str(problem.get(key) or "").strip()
        if title:
            return title
    text = str(problem.get("description") or fallback_text or "").strip()
    first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
    if "时间复杂度" in text and ("二分" in text or "mid" in text or "search(" in text):
        return "二分查找时间复杂度分析"
    if first_line:
        return first_line[:32]
    return "算法题认知学习"


def looks_code_or_algorithmic(text: str) -> bool:
    markers = (
        "def ",
        "class ",
        "int ",
        "return ",
        "for ",
        "while ",
        "if ",
        "target",
        "nums",
        "arr",
        "时间复杂度",
        "空间复杂度",
        "算法",
        "函数",
    )
    return any(marker in text for marker in markers)


def validate_problem_for_generation(problem: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    leetcode_id = int(problem.get("leetcodeId") or 0)
    title = str(problem.get("titleZh") or "").strip() or str(problem.get("titleEn") or "").strip()
    description = str(problem.get("description") or "").strip()
    if not title:
        errors.append("未识别到题目标题")
    if len(description) < 20:
        errors.append("题目描述过短，无法生成可靠学习材料")
    if leetcode_id > 0:
        if not problem.get("examples"):
            errors.append("LeetCode 题面缺少示例")
        if not problem.get("constraints"):
            errors.append("LeetCode 题面缺少约束")
    elif not looks_code_or_algorithmic(description + "\n" + str(problem.get("functionSignature") or "")):
        errors.append("未识别到可分析的算法题干或代码")
    return errors


def build_page_plan_prompt(problem: Dict[str, Any]) -> str:
    problem_text = json.dumps(problem, ensure_ascii=False, indent=2)
    return (
        PAGE_PLAN_PROMPT.replace("__PROBLEM_JSON__", problem_text)
        .replace("__EXAMPLE_BLUEPRINT__", EXAMPLE_BLUEPRINT)
    )


def audit_page_plan(plan: Dict[str, Any], problem: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    required_top = [
        "courseHeader",
        "stageTrack",
        "algorithmWorkspace",
        "tracePlayer",
        "codePractice",
        "transferLearning",
        "visualStyle",
    ]
    for key in required_top:
        if key not in plan:
            errors.append("page_plan missing %s" % key)

    course = plan.get("courseHeader") or {}
    if not str(course.get("title") or "").strip():
        errors.append("page_plan courseHeader.title is required")
    if not str(course.get("skillThesis") or "").strip():
        errors.append("page_plan courseHeader.skillThesis is required")

    stages = plan.get("stageTrack") or []
    if not isinstance(stages, list) or len(stages) < 5:
        errors.append("page_plan requires at least 5 stages")
    for index, stage in enumerate(stages[:7], start=1):
        if not str((stage or {}).get("learnerTask") or "").strip():
            errors.append("page_plan stage %s missing learnerTask" % index)
        if not str((stage or {}).get("unlockAction") or "").strip():
            errors.append("page_plan stage %s missing unlockAction" % index)

    workspace = plan.get("algorithmWorkspace") or {}
    if len(workspace.get("stateStrip") or []) < 3:
        errors.append("page_plan algorithmWorkspace.stateStrip requires at least 3 state variables")

    trace = plan.get("tracePlayer") or {}
    if len(trace.get("traceStateFields") or []) < 4:
        errors.append("page_plan tracePlayer.traceStateFields requires at least 4 fields")
    controls = set(trace.get("controls") or [])
    for control in ("prev", "next", "play", "reset"):
        if control not in controls:
            errors.append("page_plan tracePlayer.controls missing %s" % control)
    if int(trace.get("minimumFrames") or 0) < 6:
        errors.append("page_plan tracePlayer.minimumFrames must be at least 6")

    slots = ((plan.get("codePractice") or {}).get("slots") or [])
    if len(slots) < 3:
        errors.append("page_plan codePractice.slots requires at least 3 slots")

    transfer = plan.get("transferLearning") or {}
    transfer_problem = transfer.get("transferProblem") or {}
    if not str(transfer_problem.get("title") or "").strip():
        errors.append("page_plan transferLearning.transferProblem.title is required")
    if len(transfer.get("preservedConcepts") or []) < 3:
        errors.append("page_plan transferLearning.preservedConcepts requires at least 3 items")
    if len(transfer.get("changedConcepts") or []) < 3:
        errors.append("page_plan transferLearning.changedConcepts requires at least 3 items")
    if len(transfer.get("scaffoldSlots") or []) < 4:
        errors.append("page_plan transferLearning.scaffoldSlots requires at least 4 slots")
    transfer_trace = transfer.get("transferTrace") or {}
    if int(transfer_trace.get("minimumFrames") or 0) < 6:
        errors.append("page_plan transferLearning.transferTrace.minimumFrames must be at least 6")
    transfer_controls = set(transfer_trace.get("controls") or [])
    for control in ("prev", "next", "play", "reset"):
        if control not in transfer_controls:
            errors.append("page_plan transferTrace.controls missing %s" % control)
    if not str(transfer.get("proofObligation") or "").strip():
        errors.append("page_plan transferLearning.proofObligation is required")

    if int(problem.get("leetcodeId") or 0) == 209:
        transfer_blob = json.dumps(transfer, ensure_ascii=False)
        for token in ("713", "product", "right-left+1"):
            compact = transfer_blob.replace(" ", "")
            if token not in compact:
                errors.append("page_plan for LeetCode 209 transfer must include %s" % token)

    return errors


def generate_page_plan(
    problem: Dict[str, Any],
    *,
    api_key: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    timeout: int = 240,
    attempts: int = 2,
    llm_call: Callable[..., Dict[str, Any]] = chat_completion,
) -> tuple[Dict[str, Any], List[str], List[Dict[str, Any]], List[Optional[str]]]:
    prompt = build_page_plan_prompt(problem)
    usage: List[Dict[str, Any]] = []
    finish_reasons: List[Optional[str]] = []
    plan: Dict[str, Any] = {}
    errors: List[str] = []
    for _attempt in range(1, attempts + 1):
        response = llm_call(
            prompt,
            api_key=api_key,
            model=model,
            system=PAGE_PLAN_SYSTEM,
            max_tokens=12000,
            temperature=0.15,
            timeout=timeout,
            json_output=True,
            thinking="disabled",
        )
        usage.append(response.get("usage") or {})
        finish_reasons.append((response.get("choices") or [{}])[0].get("finish_reason"))
        plan = extract_json(first_message_text(response))
        errors = audit_page_plan(plan, problem)
        if not errors:
            break
        prompt = (
            build_page_plan_prompt(problem)
            + "\n\n上一次 page_plan 未通过审计，失败项如下：\n- "
            + "\n- ".join(errors)
            + "\n\n请返回完整修复后的 page_plan JSON。"
        )
    return plan, errors, usage, finish_reasons


def structure_problem_text(
    problem_text: str,
    *,
    api_key: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    timeout: int = 120,
    llm_call: Callable[..., Dict[str, Any]] = chat_completion,
) -> Dict[str, Any]:
    if not problem_text.strip():
        raise ValueError("problem text is empty")
    prompt = STRUCTURE_PROMPT.replace("__PROBLEM_TEXT__", problem_text.strip())
    response = llm_call(
        prompt,
        api_key=api_key,
        model=model,
        system=STRUCTURE_SYSTEM,
        max_tokens=4096,
        temperature=0,
        timeout=timeout,
        json_output=True,
        thinking="disabled",
    )
    problem = normalize_problem(extract_json(first_message_text(response)), fallback_text=problem_text)
    validation_errors = validate_problem_for_generation(problem)
    if validation_errors:
        raise ValueError(
            "题目文本信息不足，已停止生成："
            + "；".join(validation_errors)
            + "。请至少粘贴清晰题干；LeetCode 题建议包含题号、题名、描述、示例、约束和函数签名。"
        )
    return problem


def extract_html(text: str) -> str:
    content = text.strip()
    if content.startswith("```"):
        content = "\n".join(line for line in content.splitlines() if not line.strip().startswith("```")).strip()
    lower = content.lower()
    start = lower.find("<!doctype html")
    if start < 0:
        start = lower.find("<html")
    if start > 0:
        content = content[start:]
    return content


def direct_filename(problem: Dict[str, Any]) -> str:
    leetcode_id = int(problem.get("leetcodeId") or 0)
    slug = str(problem.get("slug") or "leetcode-problem").replace("_", "-")
    safe_slug = re.sub(r"[^a-z0-9-]+", "-", slug.lower()).strip("-") or "leetcode-problem"
    if leetcode_id > 0:
        return "direct_%03d_%s.html" % (leetcode_id, safe_slug)
    return "direct_general_%s.html" % safe_slug


def build_direct_prompt(prompt_path: Path, problem: Dict[str, Any], page_plan: Optional[Dict[str, Any]] = None) -> str:
    prompt_template = prompt_path.read_text(encoding="utf-8")
    problem_text = json.dumps(problem, ensure_ascii=False, indent=2)
    placeholder = "【在这里粘贴LeetCode题号、题名和题目描述】"
    if placeholder in prompt_template:
        prompt = prompt_template.replace(placeholder, problem_text)
    else:
        prompt = prompt_template + "\n\n# 本次题目\n\n" + problem_text
    if page_plan is not None:
        prompt += "\n\n# 本次 page_plan.json（必须严格落实到 HTML 结构和交互中）\n\n"
        prompt += json.dumps(page_plan, ensure_ascii=False, indent=2)
    prompt += MIGRATION_DEPTH_REQUIREMENTS
    prompt += EXAMPLE_QUALITY_REQUIREMENTS
    prompt += EXAMPLE_BLUEPRINT
    prompt += (
        "\n\n硬性输出要求：只输出一个完整的 HTML 文档，从 <!doctype html> 或 <html> 开始，"
        "不要 Markdown 代码围栏，不要解释文字。文件必须是单文件，CSS 和 JavaScript 内联。"
    )
    return prompt


def audit_direct_html(path: Path, problem: Dict[str, Any]) -> List[str]:
    text = path.read_text(encoding="utf-8")
    lower = text.lower()
    errors: List[str] = []

    if not (lower.lstrip().startswith("<!doctype html") or lower.lstrip().startswith("<html")):
        errors.append("direct html must start with <!doctype html> or <html")
    if "<style" not in lower:
        errors.append("direct html must inline CSS in a <style> block")
    if "<script" not in lower:
        errors.append("direct html must inline JavaScript in a <script> block")
    if "https://" in lower or "http://" in lower:
        errors.append("direct html must not reference external network resources")
    if "{{" in text or "}}" in text:
        errors.append("direct html contains unresolved template tokens")

    leetcode_id = str(problem.get("leetcodeId") or "")
    if leetcode_id and leetcode_id != "0" and leetcode_id not in text:
        errors.append("direct html must mention LeetCode id %s" % leetcode_id)
    for key in ("titleZh", "titleEn"):
        title = str(problem.get(key) or "")
        if title and title not in text:
            errors.append("direct html must mention %s: %s" % (key, title))

    if "迁移" not in text:
        errors.append("direct html must include a transfer-learning section")
    if "参考答案" not in text:
        errors.append("direct html must include transfer/reference answer access")
    has_autoplay = "自动播放" in text or "playTransfer" in text or "playBtn" in text or ">自动<" in text
    if not has_autoplay:
        errors.append("direct html must include autoplay for trace playback")

    if int(problem.get("leetcodeId") or 0) == 209:
        compact = text.replace(" ", "")
        required = {
            "713": "LeetCode 209 transfer must target LeetCode 713",
            "乘积小于": "LeetCode 209 transfer must describe product-less-than-k",
            "product": "LeetCode 209 transfer must use product state",
            "right-left+1": "LeetCode 209 transfer must include batch-count formula right-left+1",
        }
        for token, message in required.items():
            haystack = compact if token == "right-left+1" else text
            if token not in haystack:
                errors.append(message)

    return errors


def generate_direct_html(
    problem: Dict[str, Any],
    *,
    prompt_path: Path,
    output_dir: Path,
    api_key: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 384000,
    temperature: float = 0.25,
    timeout: int = 600,
    attempts: int = 2,
    llm_call: Callable[..., Dict[str, Any]] = chat_completion,
) -> DirectHtmlResult:
    problem = normalize_problem(problem)
    output_dir.mkdir(parents=True, exist_ok=True)
    problem_json = output_dir / "problem.json"
    page_plan_json = output_dir / "page_plan.json"
    output = output_dir / direct_filename(problem)
    write_json(problem_json, problem)

    page_plan, page_plan_errors, page_plan_usage, page_plan_finish_reasons = generate_page_plan(
        problem,
        api_key=api_key,
        model=model,
        timeout=timeout,
        attempts=attempts,
        llm_call=llm_call,
    )
    write_json(page_plan_json, page_plan)
    if page_plan_errors:
        report = {
            "provider": "deepseek",
            "mode": "direct-html",
            "model": model,
            "problemJson": str(problem_json),
            "pagePlanJson": str(page_plan_json),
            "prompt": str(prompt_path),
            "pagePlanStatus": "failed",
            "pagePlanErrors": page_plan_errors,
            "pagePlanUsage": page_plan_usage,
            "pagePlanFinishReasons": page_plan_finish_reasons,
            "auditStatus": "failed",
            "auditErrors": page_plan_errors,
        }
        write_json(output_dir / "direct-html-report.json", report)
        raise ValueError("page_plan 未通过审计：" + "；".join(page_plan_errors))

    prompt = build_direct_prompt(prompt_path, problem, page_plan)
    usage: List[Dict[str, Any]] = []
    finish_reasons: List[Optional[str]] = []
    audit_errors: List[str] = []

    for _attempt in range(1, attempts + 1):
        response = llm_call(
            prompt,
            api_key=api_key,
            model=model,
            system=DIRECT_HTML_SYSTEM,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout,
            json_output=False,
            thinking="disabled",
        )
        usage.append(response.get("usage") or {})
        finish_reasons.append((response.get("choices") or [{}])[0].get("finish_reason"))
        html = extract_html(first_message_text(response))
        output.write_text(html, encoding="utf-8")
        audit_errors = audit_direct_html(output, problem)
        if not audit_errors:
            break
        prompt = (
            build_direct_prompt(prompt_path, problem, page_plan)
            + "\n\n上一次生成的 HTML 未通过验收，失败项如下：\n- "
            + "\n- ".join(audit_errors)
            + "\n\n请返回完整修复后的 HTML。必须保留现有正确内容，并补齐失败项。"
        )

    report: Dict[str, Any] = {
        "provider": "deepseek",
        "mode": "direct-html",
        "model": model,
        "output": str(output),
        "problemJson": str(problem_json),
        "pagePlanJson": str(page_plan_json),
        "prompt": str(prompt_path),
        "maxTokens": max_tokens,
        "pagePlanStatus": "passed",
        "pagePlanErrors": [],
        "pagePlanUsage": page_plan_usage,
        "pagePlanFinishReasons": page_plan_finish_reasons,
        "attempts": len(usage),
        "finishReasons": finish_reasons,
        "usage": usage,
        "bytes": output.stat().st_size,
        "auditStatus": "passed" if not audit_errors else "failed",
        "auditErrors": audit_errors,
    }
    write_json(output_dir / "direct-html-report.json", report)
    return DirectHtmlResult(
        output=output,
        problem_json=problem_json,
        page_plan_json=page_plan_json,
        report=report,
        audit_errors=audit_errors,
    )


def generate_from_problem_text(
    problem_text: str,
    *,
    prompt_path: Path,
    output_dir: Path,
    api_key: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 384000,
    temperature: float = 0.25,
    timeout: int = 600,
    attempts: int = 2,
) -> DirectHtmlResult:
    problem = structure_problem_text(problem_text, api_key=api_key, model=model, timeout=timeout)
    return generate_direct_html(
        problem,
        prompt_path=prompt_path,
        output_dir=output_dir,
        api_key=api_key,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        timeout=timeout,
        attempts=attempts,
    )
