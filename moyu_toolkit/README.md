# MOYU — AI Agent Memory Toolkit

**10 memory capabilities for your AI Agent. Remember who you are across conversations. No code rewrite required.**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Dependencies](https://img.shields.io/badge/dependencies-numpy%20%7C%20requests-green)]()

MOYU is a lightweight, platform-agnostic memory layer for AI Agents. Drop it into Hermes, OpenClaw, LangChain, AutoGen, or your own Python project — your Agent gains **persistent cross-session memory** instantly.

---

## Quick Start

```bash
pip install numpy requests pyyaml
```

Copy the `moyu_toolkit/` folder into your project. Run your first memory search:

```bash
cd moyu_toolkit
python3 agent_memory.py search "what did we talk about"
```

> **Zero-config mode:** Works immediately with local fallback. Add your API key in `config.yaml` when you want semantic search.

---

## 10 Capabilities

| # | Capability | What it does |
|---|-----------|-------------|
| 1️⃣ | **TEMPR Multi-Strategy Retrieval** | Semantic + BM25 + time-weighted — always finds what you need |
| 2️⃣ | **Working Memory** | Survives context compression — remembers current task |
| 3️⃣ | **Knowledge Graph** | Auto-extracts entities & relations from conversation (JSON, no database) |
| 4️⃣ | **Self-Reflection** | Analyzes old memories on wake — finds connections & contradictions |
| 5️⃣ | **User Profile** | Auto-extracts user preferences, habits, facts from conversation |
| 6️⃣ | **Learn from Corrections** | Detects "no/don't/remember" signals — learns lessons after 3 same mistakes |
| 7️⃣ | **Deduplication** | SHA256 hash — same content never stored twice |
| 8️⃣ | **Integrity Verification** | Detects memory file tampering on wake |
| 9️⃣ | **Auto Recovery** | Automatically restores from backup when tampering detected |
| 🔟 | **Forensic Analysis** | Analyzes what changed and how — instruction override, prompt injection detection |

---

## Comparison

| | Built-in (Hermes/OpenClaw) | **MOYU** |
|--|---------------------------|----------|
| Storage | Plain text files | Vector index (1536-dim semantic) |
| Retrieval | Full text dump | **TEMPR triple strategy** |
| Working memory | ❌ None | **✅ Separate file, survives compression** |
| Knowledge graph | ❌ None | **✅ JSON-based, zero ops** |
| Self-reflection | ❌ None | **✅ Automatic** |
| User profile | ❌ Manual only | **✅ Auto-extraction** |
| Learn from corrections | ❌ None | **✅ Auto-detect & accumulate** |
| Integrity check | ❌ None | **✅ manifest + SHA256** |
| Auto recovery | ❌ None | **✅ From backup** |
| Forensic analysis | ❌ None | **✅ Tamper source analysis** |
| API switching | Fixed | **✅ Hot-swappable** |
| Platform dependency | Tied to platform | **✅ Zero binding** |
| Setup time | Out of box | **pip install, 5min** |

---

## Why MOYU

- **No platform lock-in** — Hermes, OpenClaw, LangChain, or custom Python
- **No API vendor lock-in** — DeepSeek, OpenAI, MiniMax, Doubao — switch freely
- **Zero risk sidecar** — doesn't touch your existing memory files
- **Zero barrier** — no Docker, no database, no registration required
- **Pure Python, 4 core files, fully hackable**

---

## File Structure

```
moyu_toolkit/
├── agent_memory.py          # Vector memory + TEMPR retrieval
├── active_context.py         # Working memory (survives compression)
├── knowledge_graph.py        # Entity-relation graph
├── learner.py                # Learn from user corrections
├── defense_toolkit/
│   └── integrity_checker.py  # File integrity + auto recovery
├── config.yaml               # API keys & settings (fill in yours)
└── requirements.txt
```

---

## License

MIT
