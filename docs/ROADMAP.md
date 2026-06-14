# OpenSecurity Roadmap

> 本文档描述项目的发展方向和优先级，帮助贡献者找到感兴趣的领域。所有方向都欢迎社区认领。

## 当前状态（v0.x Beta）

平台核心机制已经稳定可用，部分领域比其他领域更成熟：

| 领域 | 成熟度 | 说明 |
|------|--------|------|
| **平台基础设施** | 🟢 稳定 | Plugin、session 管理、上下文压缩自愈、任务目录、知识库按需加载 |
| **二进制逆向** | 🟢 稳定 | IDA Pro headless 工具链最完善，沉淀了大量实战脚本和知识库 |
| **Web 安全** | 🟢 稳定 | 黑/白/灰盒路径完整，覆盖常见框架和漏洞类型 |
| **移动端逆向（APK）** | 🟢 稳定 | apktool + jadx + Frida 路径完整 |
| **移动端逆向（IPA）** | 🟡 待增强 | 基础分析可用，但 native 库分析和 Swift 支持较弱 |
| **AI 安全分析** | 🟡 沉淀中 | 攻击框架可用，但方法论和 pattern 库还在积累 |
| **GUI 自动化** | 🟡 待增强 | 视觉驱动方案可用，但依赖目标程序的控件可访问性 |
| **Windows 内核驱动** | 🔴 实验性 | 需要双机调试环境，目前仅有初步支持 |
| **Coordinator 编排** | 🟢 稳定 | 复合任务拆分和分发可用 |

## v1.0 目标（近期，3-6 个月）

**主题：把已有领域做深，让平台"开箱即用"**

### 1. IPA 分析路径增强
当前 IPA 分析较薄弱，目标是达到 APK 的同等水平：

- [ ] Swift 符号解析（Demangle、Protocol Witness Table 解析）
- [ ] ObjC 方法 Hook 模板（Frida）
- [ ] iOS 应用证书与签名分析
- [ ] dyld_shared_cache 解包与分析支持
- [ ] IPA 知识库完善（参考 APK 路径的 `android-tools.md`）

**认领标签**：[`help wanted`](https://github.com/zylc369/OpenSecurity/labels/help%20wanted)、[`area: mobile`](https://github.com/zylc369/OpenSecurity/labels/area%3A%20mobile)

### 2. AI 安全攻击方法论沉淀
把零散的攻击 pattern 系统化为可复用的知识库：

- [ ] OWASP LLM Top 10 全覆盖（每类一个 pattern 文档）
- [ ] 提示注入分类（直接/间接/RAG 投毒/多轮诱导）
- [ ] 越狱技术分类（角色扮演/编码绕过/前缀注入/多语言）
- [ ] LLM 应用模拟器（白盒测试时模拟目标模型）
- [ ] Agent 框架安全测试（AutoGPT/LangChain 类应用的攻击面）

**认领标签**：[`help wanted`](https://github.com/zylc369/OpenSecurity/labels/help%20wanted)、[`area: ai-security`](https://github.com/zylc369/OpenSecurity/labels/area%3A%20ai-security)

### 3. Web 安全知识库扩展
补充主流框架和新兴攻击面：

- [ ] GraphQL 安全审计（批量查询、嵌套查询、字段建议攻击）
- [ ] Server-Side Request Forgery 专题（云元数据、内网探测）
- [ ] Prototype Pollution 模式速查
- [ ] 主流 CMS / 框架的常见配置缺陷（Django / Spring / Next.js / Nuxt）
- [ ] HTTP/2 和 HTTP/3 攻击面

**认领标签**：[`help wanted`](https://github.com/zylc369/OpenSecurity/labels/help%20wanted)、[`area: web`](https://github.com/zylc369/OpenSecurity/labels/area%3A%20web)

### 4. 工具链稳健性
让平台在更多环境下稳定运行：

- [ ] Linux 平台的 GUI 自动化（目前偏 Windows）
- [ ] IDA Pro 9.x 兼容性验证
- [ ] 工具脚本单元测试覆盖（query.py、update.py）
- [ ] 错误信息国际化（部分中文错误信息国际化为英文 + 中文双语）

**认领标签**：[`good first issue`](https://github.com/zylc369/OpenSecurity/labels/good%20first%20issue)、[`area: infra`](https://github.com/zylc369/OpenSecurity/labels/area%3A%20infra)

### 5. Windows 内核驱动分析
当前仅有初步支持，目标是达到可实战的双机调试分析能力：

- [ ] 双机调试环境搭建指南（WinDbg over network/serial）
- [ ] 驱动加载与卸载的自动化脚本
- [ ] IRP 处理函数定位与追踪（Major function 表解析）
- [ ] VMP 混淆驱动的处理策略（结合已有的 `kernel-driver-analysis.md`）
- [ ] 内核态内存读写验证工具

**认领标签**：[`help wanted`](https://github.com/zylc369/OpenSecurity/labels/help%20wanted)、[`area: kernel`](https://github.com/zylc369/OpenSecurity/labels/area%3A%20kernel)

### 6. 文档与示例
- [ ] 录制 3-5 个 Demo 视频（每个领域一个）
- [ ] CTF 解题案例集（用平台解历年真题的 writeup）
- [ ] FAQ 文档
- [ ] 英文版核心文档

**认领标签**：[`good first issue`](https://github.com/zylc369/OpenSecurity/labels/good%20first%20issue)、[`docs`](https://github.com/zylc369/OpenSecurity/labels/docs)

## 中期方向（v1.x，6-12 个月）

**主题：扩展新的安全分析领域**

### 6. 新 Agent 候选

按优先级排序，欢迎社区认领（参考 [添加新 Agent 指南](contributing/add-new-agent.md)）：

| 候选 Agent | 价值 | 难度 |
|-----------|------|------|
| **IoT 固件分析** | 独特工具链（binwalk、固件解包、嵌入式架构），IoT 安全需求大 | 高 |
| **PWN 专题** | 当前在 binary-analysis 内，独立后可专门做 ROP/堆利用自动化 | 中 |
| **区块链智能合约** | EVM 反编译、链上数据分析、DeFi 漏洞模式 | 中 |
| **恶意软件分析** | 沙箱集成、YARA 规则、家族归类 | 高 |
| **云安全** | AWS/GCP/Azure 配置审计、IAM 分析、S3 bucket 扫描 | 中 |

### 7. Coordinator 智能化

让编排器更聪明地拆分复合任务：

- [ ] 任务复杂度自动评估（简单任务不分发，直接由当前 Agent 完成）
- [ ] 子任务并行化（无依赖的子任务同时执行）
- [ ] 子任务结果冲突调解（多个子 Agent 给出矛盾结论时如何取舍）
- [ ] 学习用户的编排偏好（用户经常手动调整拆分方案 → 沉淀模式）

### 8. evolve Agent 增强

让平台"越用越强"的机制更完善：

- [ ] 自动识别"反复踩的坑"（从 timeline.log 提取模式）
- [ ] 脚本沉淀质量评分（自动判断生成的脚本是否值得沉淀）
- [ ] 知识库去重和合并（防止相似文档堆积）
- [ ] evolve 决策可解释性（输出"为什么认为这是高价值改进"）

## 长期方向（v2.x+）

**主题：从工具平台走向研究员助理**

### 9. 持续学习与个性化

- [ ] 用户知识库（每个用户/团队有自己的私有知识库）
- [ ] 协作模式（多人分析同一目标时的状态同步）
- [ ] 历史任务检索（"上次遇到类似的壳是怎么处理的"）

### 10. 自动化研究循环

- [ ] 自动监控新漏洞披露 → 触发分析 → 沉淀模式
- [ ] 自动跟踪新技术（新框架、新协议）→ 更新知识库
- [ ] 与公开 CVE/CWE 数据库联动

### 11. 多模态分析

- [ ] 分析协议抓包（pcap）→ 还原通信协议
- [ ] 分析硬件侧信道（功耗/电磁）
- [ ] 分析固件更新包（差分对比）

## 非目标

明确**不做**的事情，避免无效贡献：

- **不做 SaaS 商业服务**：OpenSecurity 是本地运行的工具平台，不提供云服务版本
- **不做绕过反病毒产品的功能**：恶意软件分析聚焦于理解和归类，不提供免杀能力
- **不集成需要付费 API 的功能到核心**：所有核心功能应可在本地完全离线运行（可选集成在线服务）
- **不破坏 IDA Pro 的原生体验**：所有 IDA 集成走 headless 模式，不修改 IDA 的 GUI 行为
- **不做 C2 框架或攻击工具集**：本平台定位为分析工具，不提供攻击基础设施

## 版本节奏

- **v0.x**：当前阶段，核心机制稳定但 API 可能调整
- **v1.0**：首个稳定版本，承诺向后兼容性
- **v1.x**：增量扩展新领域
- **v2.x**：可能涉及架构演进，提前在 Discussions 讨论

## 如何认领

1. 找到感兴趣的方向（上面的清单或自带想法）
2. 在 [GitHub Discussions](https://github.com/zylc369/OpenSecurity/discussions) 开帖说明你想做什么、打算怎么做
3. 维护者会回复反馈，必要时创建对应 issue
4. 按 [CONTRIBUTING.md](../CONTRIBUTING.md) 流程开发提 PR

我们鼓励**先讨论再开发**——尤其是新 Agent 和平台机制改动，提前对齐设计能避免后期大改。

## 维护者

Roadmap 由项目维护者维护，但**方向由社区共同塑造**。如果你认为有更重要的方向被遗漏了，欢迎在 Discussions 提出。

---

最后更新：2026-06
