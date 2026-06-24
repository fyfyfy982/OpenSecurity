# 插件代码拆分 + SessionDataManager 统一管理

## §1 背景与目标

### 来源

代码审计和讨论中发现两类问题：
1. SessionData 创建逻辑散落在 3 个地方，代码重复、职责模糊
2. 插件单文件 1500+ 行，可维护性差

两者可以合并解决——重做 session 管理时顺便拆分文件。

### 痛点

| 问题 | 当前状态 |
|------|---------|
| 插件单文件过大 | security-analysis.ts 1568 行，所有逻辑挤在一个文件 |
| SessionData 创建散落 | 3 个创建点（doEnsureSession、requireSessionWithPrimary、间接通过 chat.message），代码几乎相同 |
| 职责模糊 | ensureSession 和 requireSessionWithPrimary 功能高度重叠 |
| nonPrimarySessions 冗余 | 用单独的 Set 缓存非 PRIMARY session |
| 并发去重散落 | pendingEnsures Map 是裸露的全局变量 |
| debugLog 循环依赖 | debugLog 依赖 getTaskDir 和 getAgentName，而它们又依赖 debugLog |
| 缺少 parentSessionID | 无法判断子任务 |

### 预期收益

- 插件从 1 个文件拆分为 10 个文件，每个文件 80~400 行
- SessionData 创建点统一为 1 个（SessionDataManager.getOrCreate）
- 消除 debugLog 循环依赖
- 删除 4 个散落函数 + 3 个全局变量
- SessionData 新增 parentSessionID 字段，为编排 agent 子任务方案打基础

## §2 技术方案

### 2.1 文件拆分方案

```
.opencode/plugins/
├── security-analysis.ts    ← 主入口（~400行）：Plugin 函数 + hooks + debugLog + abortSession
├── constants.ts            ← 常量定义（~80行）
├── logging.ts              ← 日志基础设施（~60行）：writeLog、trimLogFile、getLogFilePath
├── task-session.ts         ← 任务目录映射（~80行）：getTaskDir、removeTaskSession、readJsonSafe
├── session-manager.ts      ← SessionData + SessionDataManager（~120行）
├── venv.ts                 ← Python 虚拟环境管理（~100行）
├── snippet.ts              ← 占位符展开（~80行）：loadSnippet、hasBuwaiExtensionId、parseFrontmatter
├── persistence.ts          ← 分析持续性恢复（~150行）：maybeResumeAnalysis、checkLastMessageAborted 等
├── timeline.ts             ← 时间线记录（~80行）：recordTimeline、flushTimeline
└── env-builder.ts          ← 环境信息构建（~200行）：buildEnvSection、getCompactionContext 等
```

### 2.2 依赖链（无循环）

```
constants.ts           ← 无依赖
    ↑
logging.ts             ← writeLog, getLogFilePath, trimLogFile
    ↑
task-session.ts        ← getTaskDir, removeTaskSession, readJsonSafe
    ↑
session-manager.ts     ← SessionData, SessionDataManager
    ↑
venv.ts                ← ensureVenvPython, PYTHON_CMD
    ↑
snippet.ts             ← loadSnippet, hasBuwaiExtensionId
    ↑
persistence.ts         ← maybeResumeAnalysis 等
    ↑
timeline.ts            ← recordTimeline, flushTimeline
    ↑
env-builder.ts         ← buildEnvSection, getCompactionContext
    ↑
security-analysis.ts   ← 主入口（debugLog + abortSession + 所有 hooks）
```

### 2.3 循环依赖分析与解决方案

当前代码中存在 2 个循环依赖：

**循环 1：debugLog ↔ getTaskDir**
```
debugLog → 调 getTaskDir（决定日志路径）
getTaskDir catch → 调 debugLog（记录异常）
```

**循环 2：debugLog ↔ session 管理**
```
debugLog → 调 getAgentName（决定日志路由）
doEnsureSession/requireSessionWithPrimary → 调 debugLog（记录日志）
```

**根因**：debugLog 承担了两个职责——写日志（基础设施）+ 日志路由（业务逻辑）。

**解决方案：拆分 debugLog 职责**

| 层 | 文件 | 函数 | 说明 |
|----|------|------|------|
| 基础设施 | logging.ts | `writeLog(logFile, msg)` | 纯写文件 + 时间戳，不依赖任何业务逻辑 |
| 基础设施 | logging.ts | `getLogFilePath(agentName)` | 根据 agent 名返回日志路径，只依赖 constants |
| 业务路由 | security-analysis.ts | `debugLog(msg, sessionID)` | 调 getTaskDir + sessionManager.get + writeLog，留在主文件 |

底层模块（task-session.ts、session-manager.ts 等）的 catch 块调 `writeLog(DEFAULT_LOG, msg)`，不调 debugLog。避免循环依赖。

### 2.4 SessionData 类

```typescript
// session-manager.ts
import { PRIMARY_AGENTS } from "./constants";
import { writeLog, DEFAULT_LOG } from "./logging";

export class SessionData {
  readonly createdAt: number;
  agentName?: string;
  readonly parentSessionID?: string;
  systemTransformCount = 0;

  constructor(agentName?: string, parentSessionID?: string) {
    this.createdAt = Date.now();
    this.agentName = agentName;
    this.parentSessionID = parentSessionID;
  }

  isPrimaryAgent(): boolean {
    return !!this.agentName && PRIMARY_AGENTS.includes(this.agentName);
  }

  isChildSession(): boolean {
    return !!this.parentSessionID;
  }
}
```

### 2.5 SessionDataManager 类

```typescript
// session-manager.ts
export class SessionDataManager {
  private sessions = new Map<string, SessionData>();
  private pending = new Map<string, Promise<SessionData | undefined>>();
  private client: OpencodeClient | null;

  constructor(client: OpencodeClient | null) {
    this.client = client;
  }

  /** 统一创建/获取入口。所有 session 都创建 SessionData（不管 agent 类型）。 */
  async getOrCreate(sessionID: string): Promise<SessionData | undefined> {
    const existing = this.sessions.get(sessionID);
    if (existing) return existing;

    const inFlight = this.pending.get(sessionID);
    if (inFlight) return inFlight;

    const promise = this.createFromAPI(sessionID);
    this.pending.set(sessionID, promise);
    try {
      return await promise;
    } finally {
      this.pending.delete(sessionID);
    }
  }

  /** 只返回 PRIMARY agent 的 session。不创建，委托给 getOrCreate。 */
  async requirePrimary(hookName: string, sessionID?: string): Promise<SessionData | undefined> {
    if (!sessionID) {
      writeLog(DEFAULT_LOG, `[${hookName}] 跳过 — 无 sessionID`);
      return undefined;
    }
    const session = await this.getOrCreate(sessionID);
    if (!session) return undefined;
    if (!session.isPrimaryAgent()) {
      writeLog(DEFAULT_LOG, `[${hookName}] 跳过 — 非 PRIMARY agent=${session.agentName || "无"} sessionID=${sessionID}`);
      return undefined;
    }
    return session;
  }

  /** 同步获取（不触发创建）。 */
  get(sessionID: string): SessionData | undefined {
    return this.sessions.get(sessionID);
  }

  /** 更新 agentName（chat.message 中 agent 切换时调用）。 */
  setAgentName(sessionID: string, agentName: string): void {
    const session = this.sessions.get(sessionID);
    if (session) session.agentName = agentName;
  }

  /** 删除（session.deleted 时调用）。 */
  delete(sessionID: string): void {
    this.sessions.delete(sessionID);
  }

  /** 私有：从 API 创建 SessionData。唯一的 new SessionData() 调用点。 */
  private async createFromAPI(sessionID: string): Promise<SessionData | undefined> {
    if (!this.client) {
      writeLog(DEFAULT_LOG, `SessionDataManager: client 未初始化 sessionID=${sessionID}`);
      return undefined;
    }
    try {
      const response = await this.client.session.get({ path: { id: sessionID } });
      if (response.error || !response.data) {
        writeLog(DEFAULT_LOG, `SessionDataManager: API 错误 sessionID=${sessionID}`);
        return undefined;
      }
      const sessionInfo = response.data;
      const agentName = (sessionInfo as { agent?: string })?.agent;
      const parentSessionID = (sessionInfo as { parentID?: string })?.parentID;
      const session = new SessionData(agentName, parentSessionID);
      this.sessions.set(sessionID, session);
      writeLog(DEFAULT_LOG, `SessionDataManager: 创建 sessionID=${sessionID} agent=${agentName || "无"} parentID=${parentSessionID || "无"}`);
      return session;
    } catch (e) {
      writeLog(DEFAULT_LOG, `SessionDataManager: 异常 sessionID=${sessionID} error=${e}`);
      return undefined;
    }
  }
}
```

注意：SessionDataManager 内部用 `writeLog(DEFAULT_LOG, msg)` 而非 debugLog，避免循环依赖。完整路由日志由调用方通过 debugLog 处理。

### 2.6 调用点变更对照

| 旧调用 | 新调用 | 涉及文件 |
|--------|--------|---------|
| `ensureSession(sessionID)` | `sessionManager.getOrCreate(sessionID)` | security-analysis.ts (chat.message) |
| `requireSessionWithPrimary(hook, sid)` | `sessionManager.requirePrimary(hook, sid)` | security-analysis.ts、persistence.ts (maybeResumeAnalysis) |
| `sessions.get(sid)?.agentName` | `sessionManager.get(sid)?.agentName` | security-analysis.ts (event handler、debugLog) |
| `sessions.delete(sid)` | `sessionManager.delete(sid)` | security-analysis.ts (session.deleted) |
| `getAgentName(sessionID)` | `sessionManager.get(sessionID)?.agentName` | security-analysis.ts (buildEnvSection、debugLog) |
| `nonPrimarySessions.add/delete/has` | 删除 | 不再需要 |
| `debugLog(msg, sid)` (底层模块中) | `writeLog(DEFAULT_LOG, msg)` | task-session.ts、session-manager.ts |

### 2.7 删除清单

| 删除项 | 原因 |
|--------|------|
| `interface SessionData` | 改为 class，移到 session-manager.ts |
| `const sessions = new Map<...>()` | 内聚到 SessionDataManager |
| `const nonPrimarySessions = new Set<...>()` | 所有 session 都在 sessions Map 中 |
| `const pendingEnsures = new Map<...>()` | 内聚到 SessionDataManager |
| `function getAgentName()` | 改为 sessionManager.get(sid)?.agentName |
| `function ensureSession()` | 合并到 SessionDataManager.getOrCreate |
| `function doEnsureSession()` | 合并到 SessionDataManager.createFromAPI |
| `function requireSessionWithPrimary()` | 改为 SessionDataManager.requirePrimary |

## §3 实现规范

### 3.0 改动范围

| 文件 | 改动类型 |
|------|---------|
| `.opencode/plugins/security-analysis.ts` | 重构为主入口，删除迁移出去的代码 |
| `.opencode/plugins/constants.ts` | 新建 |
| `.opencode/plugins/logging.ts` | 新建 |
| `.opencode/plugins/task-session.ts` | 新建 |
| `.opencode/plugins/session-manager.ts` | 新建 |
| `.opencode/plugins/venv.ts` | 新建 |
| `.opencode/plugins/snippet.ts` | 新建 |
| `.opencode/plugins/persistence.ts` | 新建 |
| `.opencode/plugins/timeline.ts` | 新建 |
| `.opencode/plugins/env-builder.ts` | 新建 |

### 3.1 实施步骤拆分

按依赖顺序从底层到上层逐步拆分。每步完成后 `node --check` 验证。

**步骤 1. constants.ts + logging.ts（基础层）**
- 新建 constants.ts：提取所有常量
- 新建 logging.ts：提取 writeLog、trimLogFile、getLogFilePath
- security-analysis.ts 改为 import 这两个模块
- 预估行数: ~140 新增 + ~100 删除
- 验证点: `node --check` 通过；security-analysis.ts 中不再有常量定义和 writeLog/trimLogFile/getLogFilePath 定义
- 依赖: 无

**步骤 2. task-session.ts**
- 新建 task-session.ts：提取 getTaskDir、removeTaskSession、readJsonSafe、taskDirCache
- catch 块中的 debugLog 改为 writeLog(DEFAULT_LOG, msg)
- security-analysis.ts 改为 import
- 预估行数: ~80 新增 + ~60 删除
- 验证点: `node --check` 通过
- 依赖: 步骤 1

**步骤 3. session-manager.ts（核心：SessionData + SessionDataManager）**
- 新建 session-manager.ts：定义 SessionData 类和 SessionDataManager 类
- 删除旧的 interface SessionData、sessions Map、nonPrimarySessions、pendingEnsures、ensureSession、doEnsureSession、requireSessionWithPrimary、getAgentName
- security-analysis.ts 中添加 `let sessionManager: SessionDataManager`，在 Plugin 函数中实例化
- 所有调用点替换为 sessionManager 方法
- 预估行数: ~120 新增 + ~250 删除 + ~40 修改
- 验证点:
  - `node --check` 通过
  - `grep -c "ensureSession\|requireSessionWithPrimary\|getAgentName\|nonPrimarySessions\|pendingEnsures" security-analysis.ts` 返回 0
  - `grep -c "const sessions\b" security-analysis.ts` 返回 0
- 依赖: 步骤 1、2

**步骤 4. venv.ts + snippet.ts**
- 新建 venv.ts：提取 Python venv 管理相关代码
- 新建 snippet.ts：提取占位符展开相关代码
- catch 块中的 debugLog 改为 writeLog(DEFAULT_LOG, msg)
- 预估行数: ~180 新增 + ~180 删除
- 验证点: `node --check` 通过
- 依赖: 步骤 1

**步骤 5. persistence.ts + timeline.ts**
- 新建 persistence.ts：提取 maybeResumeAnalysis、checkLastMessageAborted、getLastAssistantText、readPersistenceData、recordResumeAttempt
- 新建 timeline.ts：提取 recordTimeline、flushTimeline、formatTimelineEntry
- persistence.ts 中的 requireSessionWithPrimary 改为 sessionManager.requirePrimary
- 预估行数: ~230 新增 + ~230 删除
- 验证点: `node --check` 通过
- 依赖: 步骤 1、2、3

**步骤 6. env-builder.ts**
- 新建 env-builder.ts：提取 buildEnvSection、getCompactionContext、getCompactionReminder
- 预估行数: ~200 新增 + ~200 删除
- 验证点: `node --check` 通过
- 依赖: 步骤 1、3

**步骤 7. 最终清理**
- security-analysis.ts 确认为主入口：Plugin 函数 + hooks + debugLog + abortSession
- 确认所有 import 正确
- 确认无残留的旧代码
- 预估行数: ~30 修改
- 验证点:
  - `node --check` 通过
  - security-analysis.ts 行数 < 500
  - `wc -l .opencode/plugins/*.ts` 查看各文件行数
- 依赖: 步骤 1~6

## §4 验收标准

### 功能验收
- `node --check` 语法检查通过（所有 .ts 文件）
- 所有旧函数名在 security-analysis.ts 中零引用
- 所有旧全局变量在 security-analysis.ts 中零引用
- chat.message 正常注册 session
- system.transform 正常注入环境信息
- shell.env 正常注入环境变量
- session.idle 正常恢复

### 回归验收
- 非 PRIMARY session 执行 bash 时 shell.env 静默跳过
- PRIMARY session 执行 bash 时 shell.env 正常注入所有环境变量
- config.json 不存在时 system.transform 调 abortSession 终止会话
- 插件重启后 session 能通过 API 恢复

### 架构验收
- 10 个文件，每个文件职责单一
- 依赖链无循环（constants → logging → task-session → session-manager → ... → security-analysis）
- SessionData 的 `new` 调用只在 SessionDataManager.createFromAPI 中
- 底层模块（task-session、session-manager 等）不调 debugLog，只调 writeLog
- debugLog 只存在于 security-analysis.ts 中
- security-analysis.ts < 500 行

## §5 与现有需求文档的关系

- `2026-05-30-env-injection-fix.md`：环境变量注入迁移到 shell.env（已实施）
- `2026-05-26-plugin-inject-python-cmd.md`：PYTHON_CMD 注入（已实施）
- `2026-06-13-analysis-persistence.md`：分析持续性恢复（已实施，maybeResumeAnalysis 函数已提取）
- 本文档：插件代码拆分 + SessionDataManager 统一管理 + 循环依赖消除
