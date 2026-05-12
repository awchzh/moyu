# MOYU — AI Agent 记忆工具包

**11 大记忆能力，让 AI Agent 跨会话真正记得你是谁。**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

MOYU 是一个轻量、零平台绑定的 AI Agent 记忆层。可接入 Hermes、OpenClaw、LangChain、AutoGen 或任何自定义 Python 项目。

---

## 快速开始

```bash
pip install numpy requests pyyaml
```

把 `moyu_toolkit/` 文件夹复制到你的项目中。运行第一条搜索：

```bash
cd moyu_toolkit
python3 agent_memory.py search "我们聊过什么"
```

> **零配置模式**：首次运行自动使用本地 n-gram 模式。填好 `config.yaml` 中的 API key 后自动升级到语义检索。

---

**一条命令统领全局：**

```bash
python3 moyu_toolkit/moyu.py --help
```

所有 MOYU 功能统一入口——检索、统计、设置、演示，一个命令搞定。

**（可选）记忆自我保护 — 在误删之前阻止它：**

```bash
cd moyu_toolkit && python3 security.py setup
```

这是你记忆的第一道防火墙。跟完整性校验（事后检测篡改）不同，记忆自我保护在操作**到达记忆文件之前**就阻止它。设好密码后，删除文件、修改配置、运行外部脚本等危险操作都需验证。用户手滑 rm？其他 AI Agent 误操作？全部拦下。[查看源码 →](moyu_toolkit/security.py)

---

| # | 能力 | 说明 |
|---|------|------|
| 1️⃣ | **TEMPR 多策略检索** | 语义 + BM25 关键词 + 时间加权，三重保障 |
| 2️⃣ | **工作记忆** | 独立文件存储，上下文压缩也不丢 |
| 3️⃣ | **轻量知识图谱** | 自动提取实体关系（JSON，零数据库） |
| 4️⃣ | **自我反思** | 醒来时自动分析旧记忆，发现关联与矛盾 |
| 5️⃣ | **用户画像** | 自动从对话中提取用户偏好和事实 |
| 6️⃣ | **从纠正中学习** | 识别"不对/不要/记住"信号，3次晋升为永久规则 |
| 7️⃣ | **防重复** | SHA256 哈希去重，不会重复存储 |
| 8️⃣ | **完整性校验** | 检测记忆文件篡改 |
| 9️⃣ | **自动恢复** | 检测到篡改后自动从备份恢复 |
| 🔟 | **法医分析** | 分析篡改来源——指令覆盖、提示词注入等 |
| 1️⃣1️⃣ | **记忆自我保护** | 第一道防火墙 — 在操作到达记忆文件之前阻止误删和篡改。密码验证、自动锁定、审计留痕。 |

---

## 对比

| | 平台自带（Hermes/OpenClaw） | **MOYU** |
|--|---------------------------|----------|
| 存储方式 | 纯文本 | 向量索引 (1536维) |
| 检索方式 | 整段全读 | **TEMPR 三重策略** |
| 工作记忆 | ❌ 无 | **✅ 抗压缩** |
| 知识图谱 | ❌ 无 | **✅ JSON 文件** |
| 自我反思 | ❌ 无 | **✅ 自动** |
| 用户画像 | ❌ 手动 | **✅ 自动** |
| 学习纠正 | ❌ 无 | **✅ 自动检测与累积** |
| 完整性校验 | ❌ 无 | **✅ manifest + SHA256** |
| 自动恢复 | ❌ 无 | **✅ 从备份恢复** |
| 法医分析 | ❌ 无 | **✅ 攻击来源分析** |
| 记忆自我保护 | ❌ 无 | **✅ 事前验证，操作前拦截** |
| API 切换 | 固定 | **✅ 随意切换** |
| 平台绑定 | 绑定平台 | **✅ 零绑定** |

---

## 文件结构

```
moyu_toolkit/
├── agent_memory.py          # 向量记忆 + TEMPR 检索
├── active_context.py         # 工作记忆（抗压缩）
├── knowledge_graph.py        # 实体关系图谱
├── learner.py                # 从用户纠正中学习
├── security.py               # 记忆自我保护 — 第一道防火墙
├── moyu.py                    # 统一 CLI 入口
├── defense_toolkit/
│   └── integrity_checker.py  # 文件完整性校验 + 自动恢复
├── config.yaml               # API 配置
└── requirements.txt
```

---

## License

MIT
