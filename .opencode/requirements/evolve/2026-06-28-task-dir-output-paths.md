# 需求：IDA 脚本输出路径统一到任务目录（消除 /tmp 权限弹窗）

## §1 背景与目标

### 来源
用户复盘：安全分析过程中"时不时的"弹出 `/tmp` 权限确认，任务卡住无法全自动。用户困惑"明明有任务目录，为什么非要写 /tmp"。

### 痛点数据
- `.opencode/binary-analysis` 下 5 个脚本的 docstring 示例使用宿主机 `/tmp` 作为输出路径
- binary-analysis agent 调用 query.py / update.py / debug_dump.py / gui_capture.py 时照搬 docstring 的 `/tmp` 示例
- `/tmp` 在项目工作目录之外 → 触发 `external_directory` 关卡（默认 ask）→ 弹窗中断

### 根因
机制齐全，引导断裂：

| 层 | 状态 | 说明 |
|----|------|------|
| 机制层 | ✅ | `create_task_dir.py` → `~/bw-security-analysis/workspace/<task_id>/` |
| 权限层 | ✅ | `~/bw-security-analysis/**` 已在所有 agent 的 `external_directory` allow |
| 规则层 | ✅ | `execution-discipline.md:12,19`「所有中间文件写入 $TASK_DIR，禁止系统临时目录」 |
| 范例层 | ❌ | binary-analysis.md 阶段 A（initial_analysis）有 `$TASK_DIR` 范例；阶段 C（query/update/debug_dump）无 |
| 示例层 | ❌ | 5 个脚本 docstring 全用 `/tmp`，agent Read 脚本时直接看到，比抽象规则更显眼 |

LLM 在"prompt 抽象规则"与"脚本 docstring 具体示例"冲突时倾向照搬 docstring 示例。阶段 A 因有显式范例不弹窗；阶段 C 缺范例，agent 转 docstring → 用 `/tmp` → 弹窗。

### 预期收益
- **轮次**：消除 query/update/debug_dump/gui_capture 调用时的权限弹窗（每条 idat 调用省 1 次人工确认）
- **速度**：分析流程不再被权限确认打断，真正实现全自动
- **准确度**：不变（仅改路径约定）
- **上下文**：不变（docstring 不进 prompt；阶段 C 约定仅 +4 行）

## §2 技术方案

### 方案 1：改 5 个脚本 docstring 的 `/tmp` → `$TASK_DIR`

脚本 docstring 是 agent 通过 Read 工具查看脚本时的"事实来源"。把它改对，agent 照搬就是正确的。

路径映射：

| 脚本 | 原 `/tmp` 路径 | 改为 |
|------|---------------|------|
| query.py:28-29 | `/tmp/result.json`、`/tmp/idat.log` | `$TASK_DIR/query_result.json`、`$TASK_DIR/query.log` |
| update.py:18-19 | `/tmp/result.json`、`/tmp/idat.log` | `$TASK_DIR/update_result.json`、`$TASK_DIR/update.log` |
| update.py:21-22 | `/tmp/ops.json`、`/tmp/result.json`、`/tmp/idat.log` | `$TASK_DIR/batch_ops.json`、`$TASK_DIR/update_result.json`、`$TASK_DIR/update.log` |
| debug_dump.py:9-10 | `/tmp/unpacked.exe`、`/tmp/result.json`、`/tmp/debug.log` | `$TASK_DIR/unpacked.exe`、`$TASK_DIR/dump_result.json`、`$TASK_DIR/debug_dump.log` |
| gui_capture.py:9-10 | `--output-dir /tmp/view` | `--output-dir $TASK_DIR/views` |
| initial_analysis.py:10-11 | `/tmp/result.json`、`/tmp/initial.log` | `$TASK_DIR/initial.json`、`$TASK_DIR/initial.log` |

注：`initial_analysis.py` 虽然阶段 A 的 prompt 已用 `$TASK_DIR`，但 docstring 仍是 `/tmp`，agent Read 时会看到不一致，一并改齐。

### 方案 2：binary-analysis.md 阶段 C 补"IDA 脚本输出路径"约定

**位置决策**：放 `binary-analysis.md` 阶段 C，**不放** `execution-discipline.md`。原因：`execution-discipline.md` 被 5 个 agent 引用（binary/mobile/web/crypto/ai-security），IDA 专属范例会污染其他 4 个不用 IDA 的 agent。

在阶段 C（`{{buwai-rule:execution-discipline}}` 之后）新增一个简短约定，强化"输出必须用 $TASK_DIR"，并明确违反后果。不重复 docstring 的完整范例（避免双份维护），只给规则 + 指向 docstring。

预期新增 4-5 行（含标题）。

### 不做（明确排除）
- **不改 `_base.py` 加默认值兜底**：方案 1+2 已解决根因；`_base.py` 是高风险基础设施层，改 `IDA_OUTPUT` 默认值会改变"必须显式指定输出"的契约，收益不抵风险。
- **不开放 `/tmp` external_directory 权限**：治标不治本，且有符号链接逃逸风险（可绕过 `~/.config/opencode` deny）。
- **不处理 mobile-analysis 的 `/tmp`**：mobile 的 `/data/local/tmp` 是设备路径（adb shell 内，不触发宿主机权限），mitm 的 `/tmp/mitm` 是独立场景，不在本次痛点范围。

## §3 实现规范

### 改动范围表

| 文件 | 改动类型 | 行数 |
|------|---------|------|
| `binary-analysis/query.py` | 修改 docstring | ~2 行 |
| `binary-analysis/update.py` | 修改 docstring | ~4 行 |
| `binary-analysis/scripts/initial_analysis.py` | 修改 docstring | ~2 行 |
| `binary-analysis/scripts/debug_dump.py` | 修改 docstring | ~2 行 |
| `binary-analysis/scripts/gui_capture.py` | 修改 docstring | ~2 行 |
| `agents/binary-analysis.md` | 新增约定小节 | ~5 行 |

### 编码规则
1. docstring 只改示例路径，不改描述文字、参数说明、调用结构
2. 路径命名保持语义化（`query_result.json`、`update_result.json`、`dump_result.json` 区分不同脚本输出；日志用 `<脚本名>.log`）
3. `$TASK_DIR` 是 bash 变量写法，docstring 的 bash 示例里直接写 `$TASK_DIR/xxx`（与 binary-analysis.md:65 一致）
4. binary-analysis.md 新增约定放在阶段 C 的 `{{buwai-rule:execution-discipline}}` 引用之后、`### 循环控制` 之前

### §3.1 实施步骤拆分

**步骤 1. 修改 5 个脚本的 docstring（/tmp → $TASK_DIR）**
- 文件: `binary-analysis/query.py`、`binary-analysis/update.py`、`binary-analysis/scripts/initial_analysis.py`、`binary-analysis/scripts/debug_dump.py`、`binary-analysis/scripts/gui_capture.py`
- 预估行数: ~12 行改动（每文件 2-4 行示例）
- 验证点:
  1. 5 个文件 Python 语法检查通过：`python -c "compile(open('<file>').read(), '<file>', 'exec')"`
  2. grep 确认 `binary-analysis/` 下 docstring 无宿主机 `/tmp` 残留（`/data/local/tmp` 设备路径除外）：`grep -rn "/tmp" .opencode/binary-analysis/ | grep -v "/data/local/tmp"` 应无 docstring 示例命中
- 依赖: 无

**步骤 2. binary-analysis.md 阶段 C 补"IDA 脚本输出路径"约定**
- 文件: `agents/binary-analysis.md`
- 预估行数: ~5 行新增
- 验证点:
  1. Read 确认约定内容正确、位置正确（execution-discipline 引用之后、循环控制之前）
  2. 约定文字包含：覆盖的脚本名、必须用 `$TASK_DIR`、禁止 `/tmp`、违反后果（权限弹窗中断自动化）
- 依赖: 步骤 1（约定指向 docstring，需 docstring 已改对）

## §4 验收标准

### 功能验收
| 编号 | 标准 | 验证方式 |
|------|------|---------|
| F1 | 5 个脚本 docstring 的示例路径全部使用 `$TASK_DIR`，无 `/tmp` | grep + 人工 Read |
| F2 | binary-analysis.md 阶段 C 包含 IDA 脚本输出路径约定 | Read 确认 |
| F3 | query.py / update.py / debug_dump.py 的 docstring 示例可直接被 agent 照搬调用（路径合法、变量名正确） | 人工 Read 比对 binary-analysis.md:65 的风格 |

### 回归验收
| 编号 | 标准 | 验证方式 |
|------|------|---------|
| R1 | 5 个脚本 Python 语法检查通过 | `python -c "compile(...)"` |
| R2 | binary-analysis.md 中 `{{buwai-rule:execution-discipline}}` 占位符未被破坏 | grep 确认占位符存在 |
| R3 | `mobile-analysis` 等其他 agent 不受影响（本次未改动它们的引用） | grep 确认未触碰其他 agent 文件 |

### 架构验收
| 编号 | 标准 | 验证方式 |
|------|------|---------|
| A1 | IDA 输出路径约定只存在于 binary-analysis.md（binary 专属），未污染 execution-discipline.md（5 agent 共享） | grep 确认 execution-discipline.md 无 IDA 脚本名 |
| A2 | 路径示例只维护一份（docstring），binary-analysis.md 约定不重复完整范例（避免双份维护） | Read 确认约定是"规则 + 指向 docstring"，非完整 bash 块 |

## §5 与现有需求文档的关系

| 文档 | 关系 |
|------|------|
| `2026-04-28-task-dir-persistence.md` | **补全**：该需求建立了任务目录机制（create_task_dir.py + session 映射），但脚本侧未对齐。本次让脚本 docstring 与任务目录机制一致 |
| `2026-05-24-snailnet-review-improvements.md` | **强化**：该需求在 execution-discipline.md 加了"文件放置"规则（抽象），本次在 binary-analysis.md 阶段 C 补具体约定（落地到 IDA 脚本场景） |
| `2026-05-03-agent-prompt-snippets.md` | **参考**：共享片段机制（`{{buwai-rule:xxx}}`），本次确认 IDA 范例因归属问题不放共享片段 |

## 备注

- **Prompt 瘦身**：binary-analysis.md 展开后行数预计已 > 450（当前 320 行 + 多个片段）。本次仅 +5 行，不显著恶化。若需瘦身应作为独立后续项，不在本次范围内强行处理（避免范围蔓延）。
- **可复用知识沉淀**：本次调研得到的洞察"LLM 倾向照搬脚本 docstring 示例，示例路径必须与期望行为一致"价值较高，建议后续沉淀到 `binary-analysis/knowledge-base/script-generation.md`。本需求不包含此沉淀（聚焦主线），作为候选后续项。
- **已知遗漏（同类问题）**：`frida-17x-api.md`、`frida-17x-bridge.md` 的 frida 项目 `/tmp` 示例 —— **已在 §6 变更3 中纳入处理**（用户指出 mobile 不是独立场景）。

## §6 执行后变更记录（2026-06-28）

经用户 review 有三处变更，本节为最终实施状态（§2-§4 为初始计划，有冲突时以本节为准）。

### 变更1：方案 2 撤销
- **原计划**：binary-analysis.md 阶段 C 加"IDA 脚本输出路径"约定
- **撤销原因**：用户 review 指出 execution-discipline.md 已有通用"文件放置"规则 + docstring 已改对，方案 2 是冗余第三层，边际价值不抵 prompt 膨胀
- **结果**：约定段已删除

### 变更2：占位符策略（具体名 → `<>` 占位）
- **原计划**：docstring 用具体文件名（query_result.json 等）
- **变更**：用户选"灵活"方向，多次调用的结果文件用 `<>` 占位（如 `<查询结果>.json`），避免覆盖
- **规则**：多次调用结果文件用 `<>` 占位；固定目录/输入文件用具体名（frida-project、mitm、unpacked.exe、batch_ops.json、views）

### 变更3：范围扩展（mobile 脚本 + 知识库）
- **原计划**：仅 binary-analysis 5 脚本
- **扩展原因**：用户指出"mobile 的 mitm /tmp 不是独立场景，是遗漏"。重新全量 grep 确认 mobile-analysis 也用 `$TASK_DIR`，其脚本/知识库的宿主机 `/tmp` 同属根因
- **新增改动**：dex_dump.py、mitm_proxy.py、frida-17x-api.md、frida-17x-bridge.md（3处含上轮漏掉的 ping.js）、mitm-methodology.md

### 最终改动清单（初始 10 文件）

> ⚠ 经代码审计补充修复后扩展至 19 文件（gui_verify/process_patch/detect_kernel_debug_env/build_apk docstring + kernel-driver-analysis.md + mobile-analysis.md + process_patch $SCRIPTS_DIR 变量修复），详见 progress 文件「代码审计修复」小节。
| 文件 | 改动 |
|------|------|
| binary-analysis/query.py | docstring 占位符 `<>` |
| binary-analysis/update.py | docstring 占位符 `<>` |
| binary-analysis/scripts/initial_analysis.py | docstring 占位符 `<>` |
| binary-analysis/scripts/debug_dump.py | docstring 占位符 `<>` |
| agents/binary-analysis.md | 删除约定段 + `view`→`views`(line 228) |
| mobile-analysis/scripts/dex_dump.py | `/tmp/dex_output` → `$TASK_DIR/dex_dump` |
| mobile-analysis/scripts/mitm_proxy.py | `/tmp/mitm` → `$TASK_DIR/mitm` |
| binary-analysis/knowledge-base/frida-17x-api.md | `/tmp/project` → `$TASK_DIR/frida-project` |
| mobile-analysis/knowledge-base/frida-17x-bridge.md | `/tmp/frida-project`→`$TASK_DIR` + `/tmp/ping.js`→`$TASK_DIR` |
| mobile-analysis/knowledge-base/mitm-methodology.md | `/tmp/mitm` → `$TASK_DIR/mitm` |

### 确认排除（不改）
- `opencode-plugin-debugging.md` 的 `/tmp/oh-my-opencode.log`：插件日志客观位置，非 agent 照搬示例
- 所有 `/data/local/tmp`：adb shell 设备路径，不触发宿主机权限
- `dex_dump.py:20` 的 `BRIDGE_PROJECT_DIR=tempfile.gettempdir()`：脚本内部代码逻辑（非示例），不触发 external_directory
