# hCaptcha 本地 ONNX 自动化

> 需要**自动通过 hCaptcha 验证**（CTF bot 提交、自动注册等场景）时使用。
> 本工具基于 hcaptcha-challenger 0.10.1.post2 的本地 ONNX 推理，**不依赖任何远程视觉 API**。

---

## 1. 什么时候用

- CTF Web 题目需要提交 URL 给 bot，但 CTF 平台有 hCaptcha 保护
- 任何需要自动通过 hCaptcha checkbox/challenge 的场景
- 远程视觉 API（Gemini/OpenAI/智谱）不可用或 rate limited 时的 fallback

## 2. 怎么用

### 2.1 作为库调用

```python
import sys
sys.path.insert(0, "$AGENT_DIR/scripts")
from hcaptcha_solver import HCaptchaSolver

# 在已有的 Playwright page 上解决 hCaptcha
solver = HCaptchaSolver(max_attempts=10)
result = await solver.solve(page=page)

if result["success"]:
    token = result["token"]  # h-captcha-response token
```

### 2.2 CLI 调用

```bash
$PYTHON_CMD $AGENT_DIR/scripts/hcaptcha_solver.py --url "https://example.com/page-with-hcaptcha"
```

### 2.3 在 CTF bot 提交场景中的用法

```python
# 1. Playwright 打开 CTF 平台 challenge 页面（bypass_csp=True）
context = await browser.new_context(bypass_csp=True)
page = await context.new_page()

# 2. 登录 + 导航到 challenge + 填写表单
# ...

# 3. 用 hcaptcha_solver 解决 hCaptcha
solver = HCaptchaSolver(max_attempts=10)
result = await solver.solve(page=page)

# 4. 如果成功，token 已自动填入页面，继续提交表单
```

> **关键**：Playwright context 必须设置 `bypass_csp=True`，否则 hCaptcha 的 HSW WebAssembly 会被 CSP 阻止。

## 3. 技术原理

### 3.1 现代 hCaptcha 的二进制响应

现代 hCaptcha（2024+）的 `/getcaptcha/` API 返回 **msgpack 二进制格式**（非 JSON）。解码流程：

1. 拦截 `/hsw.js` 脚本响应，在页面中执行（注册 `window.hsw` 函数）
2. 拦截 `/getcaptcha/` 响应的 `body`（二进制 bytes）
3. 在页面中执行 `hsw(0, new Uint8Array(...body))` → 得到解密后的字节数组
4. 用 Python `msgpack.unpackb()` 解包 → 得到 challenge 数据

> CSP 阻止 `WebAssembly.instantiate()` → HSW 无法执行 → 必须用 `bypass_csp=True`。

### 3.2 本地 ONNX 推理管线

hcaptcha-challenger 0.10.1.post2 内置三类本地模型（从 GitHub releases 按需下载到本地缓存）：

| 模型类型 | 处理的 challenge 类型 | 推理引擎 |
|---------|---------------------|---------|
| ResNet | `image_label_binary`（3x3 网格选择） | onnxruntime |
| YOLOv8 | `image_label_area_select`（区域点击） | onnxruntime |
| CLIP-ViT | 零样本分类（未见过的新类别 fallback） | onnxruntime |

模型清单在 `objects.yaml`（118 个 label_alias + 35 个 YOLO ashes_of_war），通过 `label_alias` 将 challenge prompt（如 "Please click on the cat"）映射到对应的 ONNX 模型名（如 `adult_cat`）。

### 3.3 objects.yaml 恢复

objects.yaml 在 hcaptcha-challenger 的 GitHub main 分支已被删除（0.19.0 改用 Gemini）。恢复方式：

```bash
curl -o <objects_path> \
  https://raw.githubusercontent.com/QIN2DIM/hcaptcha-challenger/5dbc4481cf9f/src/objects.yaml
```

`<objects_path>` 的获取方式：
```python
from hcaptcha_challenger.onnx.modelhub import ModelHub
print(ModelHub.from_github_repo().objects_path)
```

`hcaptcha_solver.py` 的 `_ensure_objects_yaml()` 会自动执行这个恢复。

## 4. 已知限制

| 限制 | 影响 | 应对 |
|------|------|------|
| **drag-drop challenge 不支持** | "Put the missing tile" / "drag the correct block" 等拖拽类型无法解决 | 自动刷新跳过，等待遇到支持的类型 |
| **CLIP 零样本精度有限** | 不在 objects.yaml 中的 prompt 用 CLIP fallback，准确率约 30-50% | 增大 max_attempts（10-15 次）提高累计成功率 |
| **模型覆盖率** | objects.yaml 是 2023 年的，2025 年新增的 challenge prompt 可能无匹配模型 | CLIP 零样本作为 fallback |
| **原版 handler 干扰** | AgentT.\_\_init\_\_ 自动注册原版 handler，遇二进制响应报 UnicodeDecodeError | `_patch_handler` 中 `page.remove_listener` 移除原版 |
| **hcaptcha-challenger 0.19.0 被覆盖** | `--force-reinstall` 安装 0.10.1.post2 会覆盖 0.19.0 | 0.19.0 的 Gemini 方案已否决（智谱不可用），不影响 |

## 5. 预期成功率

| 场景 | 单次成功率 | 10 次累计成功率 |
|------|-----------|---------------|
| `image_label_binary`（3x3 网格） | 50-70% | 95%+ |
| `image_label_area_select` + 已有模型 | 40-60% | 90%+ |
| `image_label_area_select` + CLIP fallback | 20-40% | 70-90% |
| `image_drag_drop`（不支持） | 0%（自动刷新） | - |

> 实际成功率取决于 hCaptcha 分配的 challenge 类型分布。drag-drop 类型占比约 30-40%，会消耗 retry 次数。
