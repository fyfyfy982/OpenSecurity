# OpenSecurity Roadmap

> **English** | [中文](ROADMAP.md)

> This document describes the project's development directions and priorities, helping contributors find areas of interest. All directions welcome community contributions.

## Current Status (v0.x Beta)

The platform's core mechanisms are stable and usable, with some domains more mature than others:

| Domain | Maturity | Notes |
|--------|----------|-------|
| **Platform infrastructure** | 🟢 Stable | Plugin, session management, context compaction recovery, task directories, on-demand knowledge loading |
| **Binary reverse engineering** | 🟢 Stable | Most complete IDA Pro headless toolchain, extensive real-world scripts and knowledge base |
| **Web security** | 🟢 Stable | Complete black/white/gray-box paths, covers common frameworks and vulnerability types |
| **Mobile RE (APK)** | 🟢 Stable | Complete apktool + jadx + Frida pipeline |
| **Mobile RE (IPA)** | 🟡 Needs work | Basic analysis available, but native library analysis and Swift support are weak |
| **AI security analysis** | 🟡 In progress | Attack framework available, but methodology and pattern library still accumulating |
| **GUI automation** | 🟡 Needs work | Vision-driven approach available, but depends on target program's control accessibility |
| **Windows kernel drivers** | 🔴 Experimental | Requires dual-machine debugging setup, currently only basic support |
| **Coordinator orchestration** | 🟢 Stable | Complex task splitting and dispatching works |

## v1.0 Goals (Near-term, 3-6 months)

**Theme: Deepen existing domains, make the platform "just work"**

### 1. IPA Analysis Enhancement
IPA analysis is currently weak. Goal: reach parity with APK support:

- [ ] Swift symbol parsing (Demangle, Protocol Witness Table analysis)
- [ ] ObjC method hook templates (Frida)
- [ ] iOS app certificate and signing analysis
- [ ] dyld_shared_cache extraction and analysis support
- [ ] IPA knowledge base enrichment (reference APK's `android-tools.md`)

**Claim labels**: [`help wanted`](https://github.com/zylc369/OpenSecurity/labels/help%20wanted), [`area: mobile`](https://github.com/zylc369/OpenSecurity/labels/area%3A%20mobile)

### 2. AI Security Attack Methodology
Systematize scattered attack patterns into reusable knowledge base:

- [ ] OWASP LLM Top 10 full coverage (one pattern doc per category)
- [ ] Prompt injection classification (direct/indirect/RAG poisoning/multi-turn)
- [ ] Jailbreak technique classification (roleplay/encoding bypass/prefix injection/multilingual)
- [ ] LLM application simulator (simulate target model during white-box testing)
- [ ] Agent framework security testing (attack surfaces of AutoGPT/LangChain-style apps)

**Claim labels**: [`help wanted`](https://github.com/zylc369/OpenSecurity/labels/help%20wanted), [`area: ai-security`](https://github.com/zylc369/OpenSecurity/labels/area%3A%20ai-security)

### 3. Web Security Knowledge Base Expansion
Cover mainstream frameworks and emerging attack surfaces:

- [ ] GraphQL security auditing (batch queries, nested queries, field suggestion attacks)
- [ ] Server-Side Request Forgery deep dive (cloud metadata, internal network probing)
- [ ] Prototype Pollution pattern quick reference
- [ ] Common misconfigurations in mainstream CMS / frameworks (Django / Spring / Next.js / Nuxt)
- [ ] HTTP/2 and HTTP/3 attack surfaces

**Claim labels**: [`help wanted`](https://github.com/zylc369/OpenSecurity/labels/help%20wanted), [`area: web`](https://github.com/zylc369/OpenSecurity/labels/area%3A%20web)

### 4. Toolchain Robustness
Make the platform run reliably in more environments:

- [ ] GUI automation on Linux (currently Windows-focused)
- [ ] IDA Pro 9.x compatibility verification
- [ ] Unit test coverage for tool scripts (query.py, update.py)
- [ ] Error message i18n (some Chinese-only error messages → bilingual)

**Claim labels**: [`good first issue`](https://github.com/zylc369/OpenSecurity/labels/good%20first%20issue), [`area: infra`](https://github.com/zylc369/OpenSecurity/labels/area%3A%20infra)

### 5. Windows Kernel Driver Analysis
Currently only basic support. Goal: reach a usable dual-machine debugging analysis capability:

- [ ] Dual-machine debugging setup guide (WinDbg over network/serial)
- [ ] Automated driver load/unload scripts
- [ ] IRP handler location and tracing (Major function table parsing)
- [ ] VMP-obfuscated driver handling strategies (building on existing `kernel-driver-analysis.md`)
- [ ] Kernel-mode memory read/write verification tools

**Claim labels**: [`help wanted`](https://github.com/zylc369/OpenSecurity/labels/help%20wanted), [`area: kernel`](https://github.com/zylc369/OpenSecurity/labels/area%3A%20kernel)

### 6. Documentation & Examples
- [ ] Record 3-5 demo videos (one per domain)
- [ ] CTF case study collection (writeups using this platform on past challenges)
- [ ] FAQ document
- [ ] English translations of core documents

**Claim labels**: [`good first issue`](https://github.com/zylc369/OpenSecurity/labels/good%20first%20issue), [`docs`](https://github.com/zylc369/OpenSecurity/labels/docs)

## Mid-term Directions (v1.x, 6-12 months)

**Theme: Expand into new security domains**

### 7. New Agent Candidates

Priority-ordered, welcome community contributions (see [Adding a New Agent Guide](contributing/add-new-agent.md)):

| Candidate Agent | Value | Difficulty |
|----------------|-------|------------|
| **IoT firmware analysis** | Unique toolchain (binwalk, firmware extraction, embedded architectures), high IoT security demand | High |
| **PWN specialization** | Currently inside binary-analysis; splitting out enables dedicated ROP/heap exploitation automation | Medium |
| **Blockchain smart contracts** | EVM decompilation, on-chain data analysis, DeFi vulnerability patterns | Medium |
| **Malware analysis** | Sandbox integration, YARA rules, family classification | High |
| **Cloud security** | AWS/GCP/Azure config auditing, IAM analysis, S3 bucket scanning | Medium |

### 8. Coordinator Intelligence

Make the orchestrator smarter at splitting complex tasks:

- [ ] Automatic task complexity assessment (simple tasks handled directly without dispatching)
- [ ] Subtask parallelization (independent subtasks execute concurrently)
- [ ] Subtask result conflict resolution (when multiple sub-agents give contradictory conclusions)
- [ ] Learning user orchestration preferences (users frequently adjust split schemes → distill patterns)

### 9. evolve Agent Enhancement

Make the "stronger over time" mechanism more robust:

- [ ] Auto-identify "recurring pitfalls" (extract patterns from timeline.log)
- [ ] Script distillation quality scoring (auto-judge whether a generated script is worth keeping)
- [ ] Knowledge base deduplication and merging (prevent similar docs from piling up)
- [ ] evolve decision explainability (output "why this is considered a high-value improvement")

## Long-term Directions (v2.x+)

**Theme: From tool platform to researcher assistant**

### 10. Continuous Learning & Personalization

- [ ] User knowledge bases (each user/team has private knowledge)
- [ ] Collaboration mode (state sync for multi-user analysis of the same target)
- [ ] Historical task retrieval ("how did we handle a similar packer last time")

### 11. Automated Research Loop

- [ ] Auto-monitor new vulnerability disclosures → trigger analysis → distill patterns
- [ ] Auto-track new technologies (frameworks, protocols) → update knowledge base
- [ ] Integration with public CVE/CWE databases

### 12. Multi-modal Analysis

- [ ] Analyze protocol captures (pcap) → reconstruct communication protocols
- [ ] Analyze hardware side channels (power/EM)
- [ ] Analyze firmware update packages (diff comparison)

## Non-Goals

What we **explicitly won't do**, to prevent wasted effort:

- **No SaaS offering**: OpenSecurity is a locally-run tool platform, no cloud service version
- **No AV evasion features**: Malware analysis focuses on understanding and classification, not bypassing antivirus
- **No paid API dependencies in core**: All core features must work fully offline (optional integrations allowed)
- **No IDA Pro native experience disruption**: All IDA integration goes through headless mode, no GUI behavior modification
- **No C2 framework or attack toolkit**: This platform is an analysis tool, not attack infrastructure

## Release Cadence

- **v0.x**: Current phase, core mechanisms stable but API may change
- **v1.0**: First stable release, backward compatibility commitment
- **v1.x**: Incremental new domain expansion
- **v2.x**: May involve architectural evolution, discuss in Discussions first

## How to Claim

1. Find a direction you're interested in (from the list above or bring your own)
2. Post in [GitHub Discussions](https://github.com/zylc369/OpenSecurity/discussions) describing what you want to do and your plan
3. Maintainers will respond with feedback and create a corresponding issue if needed
4. Follow the [CONTRIBUTING.en.md](../CONTRIBUTING.en.md) workflow to develop and submit a PR

We encourage **discussing before developing** — especially for new agents and platform mechanism changes, aligning design early avoids major rework later.

## Maintainers

The roadmap is maintained by project maintainers, but **directions are shaped by the community**. If you think an important direction is missing, bring it up in Discussions.

---

Last updated: 2026-06
