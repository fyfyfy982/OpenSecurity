# 进度: hCaptcha 本地 ONNX 自动化工具

## 完成状态

| 步骤 | 状态 | 改动要点 |
|------|------|---------|
| 0. 主 venv 依赖 | ✅ | hcaptcha-challenger 0.10.1.post2 --no-deps + importlib_metadata/scikit-learn/ftfy/regex/msgpack |
| 1. hcaptcha_solver.py 核心 | ✅ | HCaptchaSolver 类（_patch_handler, _patch_selectors, solve, _get_token）|
| 2. retry + CLI | ✅ | solve() 包含完整 retry 循环，CLI __main__ 入口 |
| 3. 知识库 | ✅ | hcaptcha-solving.md（HSW 原理、ONNX 管线、CSP 绕过、限制、成功率）|
| 4. registry.json | ✅ | hcaptcha_solver 条目已注册 |
| 5. agent prompt | ✅ | web-analysis.md 工具清单 + 知识库索引（314 行 < 450）|

## 产物文件

- `$AGENT_DIR/scripts/hcaptcha_solver.py` (323 行)
- `$AGENT_DIR/knowledge-base/hcaptcha-solving.md` (120 行)
- `$AGENT_DIR/scripts/registry.json` (新增 hcaptcha_solver 条目)
- `$OPENCODE_ROOT/agents/web-analysis.md` (新增 2 行引用)
