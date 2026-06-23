# 分析-puzzlepuzzle

## 文件位置

`examples/二进制安全/puzzlepuzzle/`

- `puzzlepuzzle.py` — 主程序（基于 arcade 库的图形界面）
- `puzzlepuzzle.dat.gz` — gzip 压缩的谜题数据（解压后约 779 MB）
- `requirements.txt` — 依赖（arcade==3.1.0 等）

## 题目

**题目目录下没有任何 README 或文字说明**，所有信息需从源码本身反推。本题是一个嵌入 flag 提取逻辑的 **Shakashaka（シャカシャカ）逻辑谜题**，目标是通过求解谜题从棋盘状态中读出 `CTF{...}` 形式的 flag。

## 题目证据（如何从代码反推出题意图）

### 证据 1：胜利条件代码自报家门

`puzzlepuzzle.py` 第 234-251 行（按 Enter 的处理）：

```python
elif key == arcade.key.ENTER:
    if self.check_solution():                    # 检查解答
        for text in self.correct_texts:
            text.color = arcade.color.GREEN       # 显示 "correct!"
        ...
        self.flag_text.text = 'CTF{' + flag + '}' # 拼出 flag
    else:
        self.wrong_text.color = ...replace(a=255) # 显示 "wrong..."
```

通过 `check_solution()` 即显示 flag，否则提示错误 —— 标准 CTF 本地题模式。

### 证据 2：UI 上的操作说明是写死的字符串

第 61-64 行：

```python
self.controls_text = arcade.Text(
    'WASD/arrow keys: move\nClick: input solution\nEnter: check solution',
    ...
)
```

运行后这段文字直接显示在窗口左上角。

### 证据 3：flag 不是常量，而是从棋盘状态按 bit 拼出来的

第 238-249 行：

```python
flag_bits = ''
for r in range(height):
    for c in range(width):
        tile = get_tile(r, c)
        if 10 <= tile <= 14:
            flag_bits += str(int(11 <= tile <= 14))   # 10→'0', 11~14→'1'
    if len(flag_bits) > 0:
        break
flag = ''.join(chr(int(flag_bits[i:i+8], 2)) for i in range(0, len(flag_bits), 8))
self.flag_text.text = 'CTF{' + flag + '}'
```

→ flag 藏在数据文件的某个特定行（第一个含激活格的行）。

### 证据 4：`check_solution` 完整定义了 Shakashaka 规则

第 253-450 行的 200 行检查逻辑对应 Shakashaka 的两条规则：

1. 数字提示格（tile 1/2/3/4/15）周围的 4 邻格中三角数量必须匹配数字
2. 所有"白色连通区域"必须是矩形（通过 BFS 遍历后检查几何关系）

## 数据格式

### 数据头

| 偏移 | 长度 | 字段 |
|------|------|------|
| 0 | 4 | `width`（uint32 LE） |
| 4 | 4 | `height`（uint32 LE） |
| 8 | `(width*height+1)//2` | 打包的 nibble 数组，每格 4 bit |

每字节存 2 个 tile：偶数 idx 取高 4 位，奇数 idx 取低 4 位（见 `get_tile` 函数）。

### 实际规模

```
width  = 17268
height = 90300
total  = 1,559,300,400 个格子（约 15.6 亿）
```

→ **完全不可能手动求解，必须写自动求解器**。

### Tile 类型对照表

| Tile | 屏幕显示 | 含义 |
|------|---------|------|
| `0` | 空 | 背景/边界 |
| `1` | 🔴 红圈 | 数字提示：周围有 0 个三角 |
| `2` | 🟡 黄点 | 数字提示：周围有 1 个三角 |
| `3` | 🟢🟢 绿双点 | 数字提示：周围有 2 个三角 |
| `4` | 🔵🔵🔵 蓝三点 | 数字提示：周围有 3 个三角 |
| `15` | 🟣🟣🟣🟣 紫四点 | 数字提示：周围有 4 个三角 |
| `5` / `10` | ⬜ 白方块 | 玩家可填的空格（5=未动，10=动过又清空） |
| `6` / `11` | ◣ | 右下三角（未动 / 已动） |
| `7` / `12` | ◢ | 左下三角 |
| `8` / `13` | ◤ | 右上三角 |
| `9` / `14` | ◥ | 左上三角 |

**关键约定**：玩家点击操作只在 `5-9` 范围内演化（base=5），或在 `10-14` 范围内演化（base=10），两套互不串扰。flag 只读 `10-14` 的格子。

### Flag 区域初步扫描结果

- 第一个含 `10-14` 格的行：**r = 5**
- 该行激活格分布在 col 8426 ~ 17234，每 24 列一个，共 **368 个激活格**
- 368 bits = 46 字节 ASCII
- 初始数据中这 368 格**全为 `10`**（即全 0 bit），解出后必须按 Shakashaka 规则填成正确的 10/11-14 模式

## 玩家交互

- WASD / 方向键 → 滚动视图（棋盘 1.5 亿格，必须滚动）
- 鼠标点击 → 在 5-14 格上填三角（点击格子的 4 个象限对应 4 种三角方向，重复点击同一象限清空）
- Enter → 校验解答，正确则显示 flag

## 分析目标

**主目标**：求出 r=5 行 368 个激活格的正确填法，按 bit 顺序拼出 `CTF{...}` 的 46 字节内容。

**约束**：必须满足 `check_solution()` 的全部规则（数字提示 + 白色区域矩形性）。

## 建议分析方法

### 路线 A：直接写 SAT/SMT 求解器（Z3）

把 Shakashaka 规则形式化为约束：
- 每个可填格（tile 5/10）有 5 种取值：空 / 4 种三角
- 数字格的邻格三角数约束
- 白色区域矩形性约束（这条最难建模，需要用"白色连通块边界"或"每对相邻白格方向一致性"来刻画）

### 路线 B：先做剪枝/分块分析（**推荐先做**）

15 亿格的 SAT 几乎不可解，但：
- 大量 `0`（空背景）天然把 puzzle 切成独立小块
- flag 区域（r=5 附近）可能是一个相对小的独立子谜题
- 只需解出与 r=5 激活格连通的相关部分即可

**先验证**：r=5 的 368 个激活格是不是只依赖一个局部子图？如果是，规模可能从 15 亿降到几千，SAT 可解。

### 路线 C：找 `check_solution` 的逻辑漏洞

审计第 253-450 行的检查逻辑，看是否存在可以绕过的捷径（例如：只让 r=5 那一行通过、利用 BFS 边界 bug 等）。如果存在，可能不需要真正解谜题。

## 参考运行

```bash
cd examples/二进制安全/puzzlepuzzle
pip install -r requirements.txt
python puzzlepuzzle.py
```

（注意：图形程序，需要在有显示的环境运行；纯求解不需要启动 GUI，直接读 dat 文件即可。）

## 输出要求

- 求解脚本（推荐放 `solutions/二进制安全/puzzlepuzzle/`）
- 完整的 `CTF{...}` flag
- 解题报告（推理过程、求解方法、关键代码片段）
