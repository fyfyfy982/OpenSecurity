# hCaptcha 本地 ONNX 自动化工具

## §1 背景与目标

**来源痛点**：SekaiCTF 2026 `<\w+` challenge 分析中，hCaptcha 完全卡死了 bot 提交链路。现有工具链只有 `bot_analyze.py`（静态分析 bot 源代码），没有 hCaptcha 解决能力。智谱视觉模型（glm-4v-plus 429 rate limited；glm-4v-flash 不具备视觉推理能力）不可用。每次 bot 提交写 2000+ 行临时代码，0% 自动通过率。

**调研验证结论**：hcaptcha-challenger 0.10.1.post2（本地 ONNX + CLIP，无 LLM API 依赖）的技术路线已端到端验证通过：
- HSW 注入 + msgpack 二进制响应解码：✅
- Challenge 任务解析：✅（需修复 ValidationError）
- 本地 ONNX 推理管线（ResNet + YOLO + CLIP）：✅
- 在 SekaiCTF 真实页面上：✅（需 `bypass_csp=True`）
- 最终通过率：0%（3 个工程问题阻断，均可修复）

**预期收益**：
- 上下文：每次写 2000+ 行临时代码 → 1 个工具调用
- 轮次：从完全卡死（无限轮次）→ 1-2 轮
- 速度：从永远无法提交 → 60-120 秒
- 准确度：修复后预期 30%+ 单次成功率，配合 retry 达到 80%+ 累计成功率

## §2 技术方案

### 2.1 新增文件

| 文件 | 位置 | 说明 |
|------|------|------|
| `hcaptcha_solver.py` | `$AGENT_DIR/scripts/hcaptcha_solver.py` | hCaptcha 本地 ONNX 自动解决工具 |
| `hcaptcha-solving.md` | `$AGENT_DIR/knowledge-base/hcaptcha-solving.md` | hCaptcha 解决知识库 |

### 2.2 修改文件

| 文件 | 位置 | 改动内容 |
|------|------|---------|
| `registry.json` | `$AGENT_DIR/scripts/registry.json` | 注册 hcaptcha_solver 脚本 |
| `web-analysis.md` | `$OPENCODE_ROOT/agents/web-analysis.md` | 添加工具引用 + 知识库索引 |

### 2.3 hcaptcha_solver.py 接口设计

```
用法: $PYTHON_CMD $AGENT_DIR/scripts/hcaptcha_solver.py [选项] --url <URL>

选项:
  --url URL                 目标页面 URL（必须 http:// 或 https://）
  --sitekey KEY             hCaptcha sitekey（可选，默认自动检测）
  --max-attempts N          最大尝试次数（默认 10）
  --browser-path PATH       浏览器可执行文件路径（可选）
  --headless                无头模式（默认 False）
  --output PATH             JSON 输出路径（可选，不指定则 stdout）

输出 JSON 格式:
{
  "success": true/false,
  "token": "h-captcha-response token（成功时）",
  "attempts": N,
  "last_status": "CHALLENGE_SUCCESS | CHALLENGE_BACKCALL | ...",
  "error": "错误信息（失败时）"
}
```

作为库使用：
```python
import sys
sys.path.insert(0, "$AGENT_DIR/scripts")
from hcaptcha_solver import HCaptchaSolver

solver = HCaptchaSolver(max_attempts=10)
result = solver.solve(page=page, sitekey="...")
```

### 2.4 核心技术架构

```
hcaptcha_solver.py
├── HCaptchaSolver 类
│   ├── _patch_handler()        — 替换 hcaptcha-challenger 的网络响应处理器
│   │   ├── HSW 脚本注入        — 拦截 /hsw.js 响应，在页面中执行
│   │   ├── msgpack 二进制解码  — 拦截 /getcaptcha/ 响应，hsw 解码 → msgpack 解包
│   │   └── QuestionResp 兼容修复 — requester_question_example 类型兼容
│   ├── _patch_selectors()      — 修复过时的 iframe 选择器
│   │   ├── HOOK_CHALLENGE      — @title → @src 匹配
│   │   └── checkbox iframe     — @title → @src 匹配
│   ├── solve()                 — 主入口，自动重试循环
│   │   ├── 点击 checkbox
│   │   ├── 检查直接通过
│   │   ├── 执行 challenge（ONNX 推理）
│   │   ├── 不支持的类型 → 刷新重试
│   │   └── 失败 → 刷新重试
│   └── _get_token()            — 提取 h-captcha-response token
```

### 2.5 关键兼容修复

| 问题 | 原因 | 修复方案 |
|------|------|---------|
| 二进制响应无法解析 | 旧版 handler 用 `response.json()`，现代 hCaptcha 返回 msgpack 二进制 | 自定义 handler：hsw 解码 → msgpack.unpackb |
| QuestionResp ValidationError | `requester_question_example` 现代 hCaptcha 返回 string，旧版期望 list | monkey-patch QuestionResp 字段为 Optional |
| iframe 选择器不匹配 | 旧版用 `@title='hCaptcha challenge'`，现代用 `@src` 含 `frame=challenge` | 覆盖 `HOOK_CHALLENGE` 类属性 |
| CSP 阻止 WebAssembly | SekaiCTF CSP 不允许 `unsafe-eval` | Playwright context `bypass_csp=True` |
| objects.yaml 404 | GitHub main 分支已删除 | 从历史提交恢复（commit 5dbc4481）；fallback：缓存到本地，不存在时提示手动恢复 |
| 原版 handler 干扰 | AgentT.\_\_init\_\_ 自动注册原版 handler，遇到二进制响应报 UnicodeDecodeError 刷屏 | `_patch_handler` 中先 `page.remove_listener("response", agent.handler)` 移除原版，再注册自定义 handler |

### 2.6 架构影响

```
改动位置在架构中的定位:

web-analysis/scripts/
├── hcaptcha_solver.py       ← 新增: hCaptcha 自动解决工具
├── bot_analyze.py           ← 不修改（互补关系：bot_analyze 分析源码，hcaptcha_solver 解决验证码）
├── registry.json            ← 修改: 注册 hcaptcha_solver
└── web_helpers.py           ← 不修改

web-analysis/knowledge-base/
└── hcaptcha-solving.md      ← 新增: HSW 解码 + ONNX 推理 + CSP 绕过知识

agents/
└── web-analysis.md          ← 修改: 添加工具引用 + 知识库索引

依赖方向: 无违反。hcaptcha_solver.py 是独立脚本，不依赖 _base/_utils/_analysis
```

### 2.7 主 venv 依赖

hcaptcha-challenger 0.10.1.post2 用 `--no-deps --force-reinstall` 安装到主 venv（`~/bw-security-analysis/.venv`），手动补齐缺失依赖。这会覆盖 0.19.0（Gemini 版），但 0.19.0 的智谱方案已否决，不影响功能。

安装命令（首次使用时执行一次）：
```bash
$PYTHON_CMD -m pip install hcaptcha-challenger==0.10.1.post2 --no-deps --force-reinstall
$PYTHON_CMD -m pip install importlib_metadata scikit-image scikit-learn ftfy regex pyyaml msgpack
```

objects.yaml 需要从 GitHub 历史提交恢复（main 分支已删除），见 §2.5。

## §3 实现规范

### 3.0 改动范围表

| 文件 | 改动类型 | 预估行数 |
|------|---------|---------|
| hcaptcha_solver.py | 新增 | ~280 行 |
| hcaptcha-solving.md | 新增 | ~120 行 |
| registry.json | 修改 | ~12 行 |
| web-analysis.md | 修改 | ~8 行 |

### 3.1 实施步骤拆分

**步骤 1. 创建 hcaptcha_solver.py 核心（HSW 解码 + 兼容修复）**
- 文件: `$AGENT_DIR/scripts/hcaptcha_solver.py`
- 预估行数: ~180 行
- 验证点:
  1. `python -c "compile(...)"` 语法检查通过
  2. `$PYTHON_CMD hcaptcha_solver.py --help` 输出正确的参数说明
  3. import 成功，HCaptchaSolver 类可实例化
  4. `_patch_handler` 可替换 hcaptcha-challenger 的 handler
  5. `_patch_selectors` 可覆盖 HOOK_CHALLENGE
- 依赖: 无

**步骤 2. 扩展 hcaptcha_solver.py（retry 逻辑 + CLI 接口 + objects.yaml 恢复）**
- 文件: `$AGENT_DIR/scripts/hcaptcha_solver.py`（追加）
- 预估行数: ~100 行
- 验证点:
  1. `python -c "compile(...)"` 语法检查通过
  2. `solve()` 方法包含完整的 retry 循环
  3. CLI `--url` 参数可启动 Playwright 并导航到目标
  4. objects.yaml 恢复逻辑（从 GitHub 历史提交下载）正常
- 依赖: 步骤 1

**步骤 3. 创建知识库 hcaptcha-solving.md**
- 文件: `$AGENT_DIR/knowledge-base/hcaptcha-solving.md`
- 预估行数: ~120 行
- 验证点:
  1. 人工读一遍确认自包含性（不依赖主 prompt 上下文即可理解）
  2. 引用路径使用 `$AGENT_DIR` 变量
  3. 包含：HSW 解码原理、ONNX 推理管线、CSP 绕过、objects.yaml 恢复、已知限制
- 依赖: 步骤 1-2

**步骤 4. 更新 registry.json**
- 文件: `$AGENT_DIR/scripts/registry.json`
- 预估行数: ~12 行
- 验证点:
  1. `python -c "import json; json.load(open('registry.json'))"` JSON 格式正确
  2. 包含 hcaptcha_solver 条目，字段完整
- 依赖: 步骤 1-2

**步骤 5. 更新 web-analysis.md Agent prompt**
- 文件: `$OPENCODE_ROOT/agents/web-analysis.md`
- 预估行数: ~8 行（新增）
- 验证点:
  1. 添加 hcaptcha_solver 到工具清单
  2. 添加 hcaptcha-solving.md 到知识库索引
  3. 总行数 < 450
- 依赖: 步骤 3

## §4 验收标准

### 功能验收

**确定性验收（必须通过）**：
- [ ] `hcaptcha_solver.py --help` 输出正确的参数说明
- [ ] `HCaptchaSolver` 类可实例化
- [ ] `_patch_handler` 正确处理 HSW 注入 + msgpack 解码
- [ ] `_patch_selectors` 正确覆盖 iframe 选择器
- [ ] `solve()` 在 hCaptcha demo 页面上至少有一次能获取到 challenge 任务（qr_queue 非空）— 这是确定性的，只要 HSW + msgpack 正常就必定通过
- [ ] `solve()` 在 SekaiCTF 真实页面上（bypass_csp=True）至少有一次能获取到 challenge 任务
- [ ] 不支持的 challenge 类型自动刷新重试，不会 crash
- [ ] QuestionResp ValidationError 被修复（requester_question_example 兼容 string 和 list）
- [ ] 超时场景正确处理（返回错误 JSON，不崩溃）
- [ ] objects.yaml 从 GitHub 历史提交恢复成功
- [ ] 原版 handler 被正确移除（无 UnicodeDecodeError 刷屏）

**概率性指标（尽力而为，不阻塞验收）**：
- [ ] 最终通过率：本地 ONNX 推理精度受模型覆盖率限制，单次通过率 10-30%。配合 retry（10 次）累计通过率预期 60-80%。drag-drop 类型不支持（自动刷新跳过）。

### 回归验收
- [ ] registry.json 其他脚本条目不受影响
- [ ] web-analysis.md 其他工具引用不受影响
- [ ] 主 venv 不受影响（hcaptcha-challenger 0.10.1.post2 在独立 venv 中）

### 架构验收
- [ ] hcaptcha_solver.py 不依赖 _base.py / _utils.py / _analysis.py（独立脚本）
- [ ] 依赖方向正确：hcaptcha_solver.py ← Agent prompt（Agent 通过 bash 调用脚本）
- [ ] 文件放置位置正确：hcaptcha_solver.py 在 web-analysis/scripts/
- [ ] Agent prompt 引用了新工具和知识库

## §5 与现有需求文档的关系

独立需求，不依赖其他未完成的需求文档。与 `2026-05-03-playwright-web-render.md`（Playwright 渲染）互补：playwright-web-render 解决"渲染 SPA 页面"，hcaptcha_solver 解决"通过 hCaptcha 验证"。
