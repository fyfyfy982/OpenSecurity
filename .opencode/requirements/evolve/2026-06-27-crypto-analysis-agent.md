# 需求: 创建 crypto-analysis Agent（密码学分析，全面 + SageMath）

## §1 背景与目标

**来源痛点**: 2026-06-27 做 SekaiCTF `apbq-rsa-iv`（lattice RSA）时发现体系缺口：
- 5 个域 agent 全不对口（binary=IDA 逆向；web/mobile/ai 域不对；evolve 不解题；coordinator 路由表无 crypto）。
- 环境只有 gmpy2（大整数），**无 SageMath/fpylll**，做不了 LLL 格规约等代数攻击。

**根因**: 体系设计时未覆盖密码学赛道。

**预期收益**:
- 新增密码学分析能力（RSA/格/ECC/古典/对称/哈希全覆盖）。
- coordinator 能正确路由 crypto 任务。
- 环境具备 SageMath 检测与使用指引。

**用户决策**: 范围=全面；格工具=SageMath（非 fpylll）；粒度=一步到位。

## §2 技术方案

### 2.1 新建 Agent 文件

`.opencode/agents/crypto-analysis.md`，frontmatter 参照 web-analysis：
```yaml
---
description: 密码学分析 — 输入密码学题目（脚本/参数/密文）和分析需求，自动完成密码学攻击与 flag 求解
mode: all
buwai-extension-id: crypto-analysis
permission:
  external_directory:
    ~/bw-security-analysis/**: allow
    ~/Downloads/**: allow
---
```
Prompt 结构（镜像 web-analysis）：角色 → 运行环境（`{{buwai-rule:running-environment}}`）→ 任务初始化（`{{buwai-rule:task-initialization}}`）→ 分析框架（识别 crypto 类型 → 读对应知识库 → SageMath/gmpy2 求解 → 验证）→ 核心原则 → 工具清单 → 知识库索引 → 输出格式 → 任务存档 → 安全规则。

**工具清单**：`sage`（CLI，格/代数/数论）、`gmpy2`、`sympy`、Python、fpylll（可选辅助）。

### 2.2 新建知识库（全面，6 篇）

`.opencode/crypto-analysis/knowledge-base/`：

| 文件 | 覆盖 |
|------|------|
| `crypto-methodology.md` | 总方法论：识别密码类型 + 路由 + SageMath 使用基础 |
| `rsa-attacks.md` | RSA：共模/小 e/Wiener/Boneh-Durfee/Coppersmith/padding oracle/低私钥指数 |
| `lattice-attacks.md` | 格攻击：LLL/HNP/截断/隐含线性关系（含 `a*p+b*q` 提示模式） |
| `ecc-attacks.md` | 椭圆曲线：Smart(anomalous)/MOV/Pohlig-Hellman/invalid curve |
| `classical-crypto.md` | 古典：替换/维吉尼亚/频率分析/Playfair/培根等 |
| `symmetric-and-hash.md` | 对称+哈希：AES 模式(ECB/CBC padding oracle)/CBC bit flip/哈希长度扩展/弱随机 |

每篇写"什么场景、怎么识别、怎么攻击、可操作步骤 + SageMath 代码片段"，遵循 `$SHARED_DIR/knowledge-base/knowledge-writing-guide.md`。

### 2.3 Plugin 注册（高风险）

`plugins/lib/constants.ts`：
- 加 `export const AGENT_CRYPTO_ANALYSIS = "crypto-analysis";`
- `SECURITY_AGENTS` 数组加 `AGENT_CRYPTO_ANALYSIS,`
- `AGENT_SCRIPT_DIRS` 由循环自动派生 → `$AGENT_DIR=.opencode/crypto-analysis/`。

### 2.4 Coordinator 路由

`security-coordinator.md` 加 crypto 路由分支：任务含 RSA/lattice/ECC/密码/cipher/hash/加密/解密 → 分发 crypto-analysis。

### 2.5 环境检测

`detect_env.py` 加 `sage` 检测（`sage --version`，作为可选工具，缺失不阻断）；setup-guide 加 SageMath 安装段（**推荐 conda: `conda install -c conda-forge sage`**；备选 macOS `brew install --cask sage-mac`、Linux `apt install sagemath`）。**不在进化中强制安装**。

### 2.6 架构文档同步

`security-analysis-evolve.md` 与 `security-coordinator.md` 的架构树补 `crypto-analysis/`。

## §3 实现规范

### 改动范围表

| 项目 | 内容 |
|------|------|
| 新增文件 | agent 1 + 知识库 6 = 7 |
| 修改文件 | constants.ts、security-coordinator.md、detect_env.py、setup-guide.md、security-analysis-evolve.md（共 5） |
| 高风险 | constants.ts（plugin）、detect_env.py（环境检测） |
| SageMath 安装 | 不自动装，仅检测 + 指南 |

### §3.1 实施步骤拆分

```
步骤 1. Plugin 注册 crypto-analysis
  - 文件: plugins/lib/constants.ts（+2 行）
  - 验证: node --check 通过；AGENT_SCRIPT_DIRS 含 crypto-analysis
  - 依赖: 无

步骤 2. Agent 目录 + crypto-analysis.md（prompt 主体）
  - 文件: .opencode/agents/crypto-analysis.md
  - 预估: ~150 行
  - 验证: frontmatter 合规、mode:all、引用 buwai-rule 片段正确、知识库索引齐全
  - 依赖: 步骤 1

步骤 3. crypto-methodology.md（总方法论 + SageMath 基础）
  - 预估: ~150 行；验证: 自包含、覆盖类型识别与路由
步骤 4. rsa-attacks.md
  - 预估: ~150 行；验证: 覆盖 6+ 种 RSA 攻击、含 sage 代码片段
步骤 5. lattice-attacks.md（含 a*p+b*q 模式，直接服务本题）
  - 预估: ~150 行；验证: 含 HNP/LLL 构造、sage 代码
步骤 6. ecc-attacks.md
  - 预估: ~120 行；验证: 含 Smart/MOV/Pohlig-Hellman
步骤 7. classical-crypto.md
  - 预估: ~120 行；验证: 含频率分析/常见古典识别
步骤 8. symmetric-and-hash.md
  - 预估: ~120 行；验证: 含 padding oracle/长度扩展

步骤 9. Coordinator 路由加 crypto 分支
  - 文件: security-coordinator.md；验证: 含 crypto 关键词路由
步骤 10. detect_env.py 加 sage 检测 + setup-guide 安装段
  - 验证: detect_env 输出含 sage 字段；python -c compile 通过
步骤 11. 架构树同步（evolve + coordinator）
  - 验证: 两处架构树含 crypto-analysis/

步骤 12. 端到端验证
  - 验证: ① node --check plugin；② crypto-analysis 出现在 SECURITY_AGENTS；③ agent 文件可被 opencode 加载（frontmatter 可解析）；④ 用 apbq-rsa-iv 回归对照——lattice-attacks.md 覆盖 a*p+b*q 提示模式
  - 依赖: 全部
```

## §4 验收标准

### 功能验收
- [ ] crypto-analysis agent 文件存在，frontmatter mode:all
- [ ] 6 篇知识库齐全且自包含
- [ ] constants.ts 注册 crypto-analysis，plugin node --check 通过
- [ ] coordinator 含 crypto 路由
- [ ] detect_env 检测 sage
- [ ] setup-guide 含 SageMath 安装（conda 为主）

### 回归验收
- [ ] 不破坏现有 5 agent 的注册（SECURITY_AGENTS 仍含全部）
- [ ] web-analysis 等现有 agent prompt 未被改动
- [ ] detect_env 现有检测项不受影响

### 架构验收
- [ ] agent 位于 `.opencode/agents/`、知识库位于 `.opencode/crypto-analysis/knowledge-base/`
- [ ] `$AGENT_DIR` 对 crypto-analysis 正确解析为 `.opencode/crypto-analysis/`
- [ ] evolve/coordinator 架构树含 crypto-analysis

## §5 与现有需求文档的关系

呼应 `2026-05-05-web-analysis-agent.md`（web-analysis 创建范本，本需求参照其结构）。独立需求，不依赖其他。
