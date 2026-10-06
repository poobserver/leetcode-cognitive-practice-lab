# 内容格式

`scripts/build_lesson.py` 使用 UTF-8 JSON。字段里的字符串按纯文本显示，不放 HTML 标签。题面以中文概括而不是复制整篇题目。查看完整可运行示范：执行 `scripts/demo_binary_search.py` 后阅读生成的 `lesson.json`。

```json
{
  "meta": {"id":704,"title":"二分查找","slug":"binary-search","difficulty":"Easy","tags":["二分"],"source":"https://leetcode.com/problems/binary-search/"},
  "problem": {"summary":"……","signature":"class Solution:\n    def search(self, nums, target):\n        pass","constraints":["……"],"examples":[{"input":"nums = […], target = …","output":"……","purpose":"……"}]},
  "model": {"headline":"候选是一个仍可能包含目标的闭区间","state":"……","contract":"……","operation":"……","invariant":"……","boundary":"……","answer":"……","complexity":{"time":"O(log n)","space":"O(1)"}},
  "ladder": [{"title":"……","detail":"……","problem":"#704 二分查找","current":true}],
  "cases": [{"id":"normal","name":"正常：目标存在","purpose":"……","input":{"nums":[2,5,8],"target":5},"expected":1,"frames":[{"caption":"……","operation":"……","line":4,"state":{"left":0,"right":2,"mid":1},"view":{"type":"array","values":[2,5,8],"pointers":{"left":0,"mid":1,"right":2},"active":[1],"discarded":[]},"question":{"prompt":"……","choices":[{"text":"……","correct":true,"feedback":"……"},{"text":"……","correct":false,"feedback":"……"}]}}]}],
  "stages": [{"title":"概念诊断","goal":"……","notes":["……"],"case":"normal","questions":[]}],
  "code": {"starter":"公开签名加 pass","skeleton":"if {{condition}}:\n    return {{result}}","slots":[{"id":"condition","label":"边界条件","hint":"何时已没有候选？","accepted":["left > right"]},{"id":"result","label":"失败返回","hint":"返回约定中的未命中值","accepted":["-1"]}],"reference":"完整、已验证的参考代码","checklist":["……"]},
  "transfer": {"title":"……","source":"……","summary":"……","preserved":["……"],"changed":["……"],"newProof":"……","starter":"公开签名加 pass","reference":"已验证的迁移参考代码","checklist":["……"],"questions":[],"cases":[]}
}
```

示意省略的内容要填为本题真实数据。默认模板 `stages` **恰好六项**，前四项可带问题与指定案例，第四项显示轨迹播放器，第五项显示代码槽位，第六项提供“独立重写 / 迁移任务”两个自由切换入口。迁移内部的“理解与轨迹 / 独立迁移代码”也是分开的自由入口，防止用旁边的推演直接拼出代码。无需手写 DOM 或沿用旧课程 state 对象。

## 字段约束

- `meta.source`、`transfer.source` 只放已确认的官方题目 URL，可为空；迁移也可为本题的条件变式，不编造题号。
- `model` 的六个语义字段都要具体填写；`ladder` 至少三项并至少一项 `current:true`。
- `cases` 至少三项，涵盖正常、反例、边界。每项 `frames` 非空；第四模块可选择所有案例并手动前进/后退。`stages[i].case` 必须指向真实案例 ID。
- 问题至少有两个选项且恰好一个正确项；每个选项都给反馈。至少一帧有读取具体可视状态的问题。错误反馈不要直接告诉正确选项编号。
- `code.skeleton` 中每个 `{{id}}` 对应一个 `slots` 项，且每个槽位实际出现在骨架中。`accepted` 是此关键表达式的合理候选，不用于验证整个程序。空值不会被接受。
- `starter` 可以提供类型导入、类名、公开签名、`pass` 与简短“在此实现”注释，不包含算法主体。`reference` 要与案例执行结果一致。
- 迁移至少包含一次关键契约变化、两个用途不同的案例和一个诊断问题。迁移的案例仍由真实解法生成帧。
- 题目样例可在概览出现；编码模块不显示整段参考答案、已完成槽位或代码轨迹。

## 可视化

`view.type` 取以下值；每帧可使用不同表示。

- `array`：`values` 数组，`pointers` 标签→索引，`active`/`discarded` 索引数组。指针越界时在数组下方显式显示，不伪画在其他元素上。
- `table`：`columns` 表头数组、`rows` 二维数组，`active` 行号数组。适合 DP、堆优先级、队列和多帧变量。
- `graph` / `tree`：`nodes` 为 `{id,label,x,y,status}` 数组；`edges` 为 `{from,to,label,dashed}` 数组；`width`/`height` 为坐标范围；可选 `axis` 为镜像轴 x 坐标。`status` 可为 `active`、`returned`、`missing`。布局来自题目结构；重复值使用不同 ID，None 是有身份的缺失位置。
- `state`：只有字段卡片，无额外图形。只适用于状态本身就是主要表示的帧，不用它替代所有图示。

图结构的坐标、边端点、节点间距会被构建脚本检查。`nodes[].label` 不宜超过约六个可视字符；长说明放在帧 caption。对结构变化可提供每帧不同的边集与节点集，不能用改变数字代替改变引用。

## 与课程主页集成

仅在确有主页且用户需要时传 `--home ../index.html`，构建器会按输出文件位置校验目标存在。没有主页参数时，页面提供返回概览按钮。构建器不会修改已有首页。
