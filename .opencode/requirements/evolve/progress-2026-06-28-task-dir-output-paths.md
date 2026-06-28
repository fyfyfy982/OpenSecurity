# 进度：IDA 脚本输出路径统一到任务目录

需求文档: 2026-06-28-task-dir-output-paths.md（含 §6 执行后变更记录）

## 初始步骤（已完成）
- 步骤1: 5 脚本 docstring /tmp → $TASK_DIR ✅
- 步骤2: binary-analysis.md 约定段 ✅ → **后撤销**（用户 review 判定冗余）

## 执行后变更（用户 review 触发，见需求文档 §6）
- 变更1: 方案2 撤销，删除约定段 ✅
- 变更2: 占位符 [中文] → `<>`（灵活方向）✅
- 变更3: 范围扩展 — mobile 脚本 + 知识库（用户指出 mobile 非独立场景）✅
  - dex_dump.py、mitm_proxy.py
  - frida-17x-api.md、frida-17x-bridge.md（3处，含上轮漏的 ping.js）、mitm-methodology.md
- 附带: binary-analysis.md view→views（line 228 对齐）✅

## 验证
- 6 py 语法检查 ✅
- 全量 grep 宿主机 /tmp 无残留（除 opencode-plugin-debugging.md 客观日志）✅
- 占位符统一 `<>` ✅
- 约定段已删 ✅

## 审计观察项（不阻塞，潜在后续）
- mitm CA 持久化：$TASK_DIR/mitm 每次新建 → CA 不复用，可能需重装设备 CA。后续可改 ~/bw-security-analysis/ 下固定资产目录
- frida-project npm install 复用：同理，每次新 task_dir 需重装 npm 依赖

## 衍生一致性修复（用户 review 发现）
- gui-automation.md 的 view（单数，7处）与 docstring/工具表的 views（复数）不一致 → 全部统一为 views ✅
- gui-interact-pc.md（命令）的 view/ → views/ ✅
- 教训：改路径名时必须全量 grep 该 token，不能只改眼前文件

## 第二轮全量载体扫描（用户指出 registry.json + 命令文件漏改）
- registry.json（3个文件）全部扫描 example_call/usage 的输出路径：
  - binary: gui_verify/process_patch 的相对 `result.json` → `$TASK_DIR/<占位>.json`
  - mobile: dex_dump/mitm_proxy/build_apk 的裸 `<DIR>` → `$TASK_DIR/<占位>`
  - binary: debug_dump/initial_analysis 的 result.json → 占位符（对齐 docstring）
  - binary: gui_capture view → views
- 教训：路径一致性要覆盖**所有载体**（docstring + registry.json + 命令文件 + 知识库），registry.json 是第三类漏掉的载体

## 整体状态: ✅ 全部完成（13 文件改动）

## 代码审计修复（审计周期1发现）
- 改 registry 漏 docstring/prompt/知识库的系统性载体遗漏，全部补齐：
  - gui_verify.py docstring（4处相对路径）→ $TASK_DIR/<占位>
  - process_patch.py docstring（相对路径）+ $SCRIPTS_DIR 无效变量 → $SHARED_DIR
  - detect_kernel_debug_env.py docstring（2处相对 env.json）→ $TASK_DIR
  - kernel-driver-analysis.md（相对 env.json）→ $TASK_DIR
  - mobile-analysis.md build_apk 工具表（相对 app.apk）→ $TASK_DIR
  - build_apk.py epilog（2处相对 myapp.apk）→ $TASK_DIR
- 教训：改任何载体（registry/docstring/prompt/知识库）时，必须 grep 该脚本名在所有载体的引用，同步更新

## 审计后整体状态: ✅ 全部完成（19 文件改动）
