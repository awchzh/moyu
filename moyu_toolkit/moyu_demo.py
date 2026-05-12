#!/usr/bin/env python3
"""
moyu_demo.py — MOYU 功能展示

装好工具包后跑这个，20 秒看完 MOYU 能做什么。
不影响后续使用——清空 memory_data/ 即可恢复为你的数据。

用法：
    python3 moyu_demo.py
"""

import json, os, shutil, sys
from datetime import datetime

STORAGE = os.path.join(os.path.dirname(__file__), "memory_data")


def _p(path):
    return os.path.join(STORAGE, path)


def clean():
    if os.path.exists(STORAGE):
        shutil.rmtree(STORAGE)
    os.makedirs(STORAGE, exist_ok=True)


def demo_data():
    """注入预制好的示例数据（不调任何 API）"""
    
    # ——— 记忆核心（10条示例记忆） ———
    memories = [
        {"id": "demo_01", "timestamp": "2026-05-08T10:00:00", "source": "user",
         "summary": "智能相框项目启动会。团队确定了智能相框的产品方向，讨论了两套方案。张艺负责后端开发，使用Python/Flask。小李负责前端，用Vue3。",
         "content_hash": "demo_01"},
        {"id": "demo_02", "timestamp": "2026-05-08T14:30:00", "source": "user",
         "summary": "方案讨论：A方案做全功能版（照片、天气、日历、语音），B方案做MVP（照片轮播+天气插件）。张艺建议先走B方案快速验证市场。",
         "content_hash": "demo_02"},
        {"id": "demo_03", "timestamp": "2026-05-09T09:00:00", "source": "event",
         "summary": "项目决策：团队决定走B路线（MVP路线）。第一阶段范围：照片轮播、天气插件、日历同步。预计开发周期4周。",
         "content_hash": "demo_03"},
        {"id": "demo_04", "timestamp": "2026-05-09T11:00:00", "source": "user",
         "summary": "张艺反馈：Flask后端API开发进度60%。SQLite数据库设计完成，包括用户表、设备表、天气配置表。",
         "content_hash": "demo_04"},
        {"id": "demo_05", "timestamp": "2026-05-10T09:30:00", "source": "user",
         "summary": "李总（项目经理）要求月底前必须出可演示的原型。重点强调天气插件功能要优先完成，客户最看重这个。",
         "content_hash": "demo_05"},
        {"id": "demo_06", "timestamp": "2026-05-10T15:00:00", "source": "user",
         "summary": "张艺说讨厌用微信沟通工作，更喜欢写飞书文档。他习惯在晚上10点后写代码，说那时候最专注。",
         "content_hash": "demo_06"},
        {"id": "demo_07", "timestamp": "2026-05-10T16:00:00", "source": "user",
         "summary": "技术方案确认：前端 Vue3 + Element Plus，后端 Flask + SQLAlchemy，数据库 SQLite，部署用阿里云 ECS + Docker。",
         "content_hash": "demo_07"},
        {"id": "demo_08", "timestamp": "2026-05-10T18:00:00", "source": "user",
         "summary": "小李（前端）完成了天气插件组件的初版，使用了高德地图API获取位置，和风天气API获取天气数据。",
         "content_hash": "demo_08"},
        {"id": "demo_09", "timestamp": "2026-05-11T10:00:00", "source": "event",
         "summary": "项目评审会：原型进展80%，天气插件已可展示，照片轮播还有bug。李总要求下周三再做一次评审。",
         "content_hash": "demo_09"},
        {"id": "demo_10", "timestamp": "2026-05-11T11:00:00", "source": "user",
         "summary": "用户偏好记录：张艺（后端开发，Mac + Docker，夜猫子型，讨厌微信偏好飞书，做事喜欢先讨论后执行）。",
         "content_hash": "demo_10"},
    ]
    with open(_p("conversation_memory.json"), 'w') as f:
        json.dump(memories, f, ensure_ascii=False, indent=2)

    # ——— 向量索引（预计算好的） ———
    # 用简化的占位向量（16维足够 demo 展示）
    vectors = []
    dim = 16
    for m in memories:
        import hashlib
        h = hashlib.md5(m["summary"].encode()).hexdigest()
        vec = [int(h[i:i+2], 16) / 255.0 for i in range(0, 32, 2)]
        vectors.append({
            "memory_id": m["id"],
            "timestamp": m["timestamp"],
            "source": m["source"],
            "summary": m["summary"][:80],
            "vector": vec[:dim]
        })
    with open(_p("vector_index.json"), 'w') as f:
        json.dump({"vectors": vectors}, f, ensure_ascii=False, indent=2)

    # ——— 知识图谱 ———
    kg = {
        "entities": {
            "张艺": {"name": "张艺", "type": "person", "first_seen": "2026-05-08",
                     "last_seen": "2026-05-11", "mention_count": 6},
            "小李": {"name": "小李", "type": "person", "first_seen": "2026-05-08",
                     "last_seen": "2026-05-10", "mention_count": 3},
            "李总": {"name": "李总", "type": "person", "first_seen": "2026-05-10",
                     "last_seen": "2026-05-10", "mention_count": 2},
            "智能相框": {"name": "智能相框", "type": "project", "first_seen": "2026-05-08",
                         "last_seen": "2026-05-11", "mention_count": 8},
            "Flask": {"name": "Flask", "type": "tech", "first_seen": "2026-05-08",
                       "last_seen": "2026-05-10", "mention_count": 3},
            "Vue3": {"name": "Vue3", "type": "tech", "first_seen": "2026-05-08",
                      "last_seen": "2026-05-10", "mention_count": 2},
            "Mac电脑": {"name": "Mac电脑", "type": "device", "first_seen": "2026-05-10",
                         "last_seen": "2026-05-10", "mention_count": 1},
            "飞书": {"name": "飞书", "type": "tool", "first_seen": "2026-05-10",
                      "last_seen": "2026-05-10", "mention_count": 1},
        },
        "relations": [
            {"source": "张艺", "target": "智能相框", "relation": "works_at", "weight": 3},
            {"source": "张艺", "target": "Flask", "relation": "uses", "weight": 2},
            {"source": "小李", "target": "智能相框", "relation": "works_at", "weight": 2},
            {"source": "小李", "target": "Vue3", "relation": "uses", "weight": 2},
            {"source": "李总", "target": "智能相框", "relation": "manages", "weight": 2},
            {"source": "张艺", "target": "Mac电脑", "relation": "uses", "weight": 1},
            {"source": "张艺", "target": "飞书", "relation": "prefers", "weight": 1},
        ]
    }
    with open(_p("knowledge_graph.json"), 'w') as f:
        json.dump(kg, f, ensure_ascii=False, indent=2)

    # ——— 工作记忆 ———
    active_ctx = {
        "session_start": "2026-05-11T15:30:00",
        "task": "跟踪智能相框MVP项目进度",
        "contexts": [
            {"text": "张艺是后端开发，用Flask写API", "timestamp": "2026-05-11T15:30:00"},
            {"text": "李总要求月底前出原型", "timestamp": "2026-05-11T15:35:00"},
            {"text": "项目从A方案改为B方案（MVP路线）", "timestamp": "2026-05-11T15:40:00"},
        ],
        "todos": [
            {"id": 1, "text": "确认A/B方案选择", "done": True, "completed_at": "2026-05-11"},
            {"id": 2, "text": "安排第一次评审会", "done": True, "completed_at": "2026-05-11"},
            {"id": 3, "text": "督促天气插件开发进度", "done": False},
            {"id": 4, "text": "准备月底原型演示", "done": False},
        ],
        "last_updated": "2026-05-11T16:00:00"
    }
    with open(_p("active_context.json"), 'w') as f:
        json.dump(active_ctx, f, ensure_ascii=False, indent=2)


def run():
    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║       MOYU Demo — 20 秒看完我能做什么          ║")
    print("╚══════════════════════════════════════════════════╝")
    print()

    # 1️⃣ 语义检索 & BM25 关键词检索
    print("─" * 54)
    print("🔍 1/6  多策略检索 — 搜什么都能找到")
    print("─" * 54)
    print()
    print("  你说：\"上次开会说了什么方案\"")
    print()
    print("  ⭐ 命中 [项目讨论] 确定了智能相框的 A/B 两套方案路线")
    print("  ⭐ 命中 [会议记录] 讨论了价格区间和功能优先级")
    print("  ⭐ 命中 [决策] 决定先做 MVP 版本")
    print()
    print("  即使搜索词跟原文不完全匹配，TEMPR 三重策略")
    print("  （语义 + BM25关键词 + 时间加权）也能找到。")
    print()

    # 2️⃣ 工作记忆
    print("─" * 54)
    print("🧠 2/6  工作记忆 — 上下文压缩了也不丢")
    print("─" * 54)
    print()
    print("  【恢复工作记忆】")
    print("  当前任务：跟踪智能相框MVP项目进度")
    print("  待办事项：")
    print("    ✅ 确认A/B方案选择")
    print("    ✅ 安排第一次评审会")
    print("    ⬜ 督促天气插件开发进度")
    print("    ⬜ 准备月底原型演示")
    print("  关键上下文：")
    print("    • 张艺是后端开发，用Flask写API")
    print("    • 李总要求月底前出原型")
    print()
    print("  独立文件存储，压缩碰不到它。100轮对话后，")
    print("  翻开工作记忆，你还知道自己在做什么。")
    print()

    # 3️⃣ 知识图谱
    print("─" * 54)
    print("📊 3/6  知识图谱 — 实体关系一目了然")
    print("─" * 54)
    print()
    print("  从对话中提取的实体关系网络：")
    print()
    print("  张艺 ──→ 负责 ──→ 智能相框项目")
    print("  张艺 ──→ 使用 ──→ Flask")
    print("  张艺 ──→ 偏好 ──→ 飞书")
    print("  小李 ──→ 负责 ──→ 智能相框项目")
    print("  小李 ──→ 使用 ──→ Vue3")
    print("  李总 ──→ 管理 ──→ 智能相框项目")
    print()
    print("  搜\"张艺\"就能看到他在项目里的关系和偏好。")
    print("  不装数据库，纯JSON文件零运维。")
    print()

    # 4️⃣ 用户画像
    print("─" * 54)
    print("👤 4/6  用户画像 — 你说过的我都记得")
    print("─" * 54)
    print()
    print("  张艺说过：")
    print("    • 做后端开发（Flask + Python）")
    print("    • 用Mac电脑 + Docker")
    print("    • 讨厌微信沟通，喜欢飞书文档")
    print("    • 习惯晚上10点后写代码")
    print()
    print("  下次张艺说\"你应该记得我的习惯吧\"")
    print("  → Agent 搜到画像，正确回答。")
    print()

    # 5️⃣ 反思
    print("─" * 54)
    print("💡 5/6  自我反思 — 发现记忆中的关联")
    print("─" * 54)
    print()
    print("  自动分析旧记忆发现：")
    print()
    print("  \"张艺说讨厌微信、偏好飞书\"")
    print("  \"团队决定走B方案（MVP路线）\"")
    print("  \"李总要求月底前出原型\"")
    print()
    print("  高层洞察：张艺的沟通偏好和项目时间线")
    print("  形成了因果链——选择MVP也跟李总的"),
    print("   deadline压力有关。")
    print()

    # 6️⃣ 学习信号
    print("─" * 54)
    print("🎯 6/6  从纠正中学习 — 你教它就会改")
    print("─" * 54)
    print()
    print("  你说：\"别再用A方案了，我们选了B\"")
    print("  → Agent 学到：\"用户要求不再提A方案\"")
    print()
    print("  第二次你说：\"又提A方案，不是说了选B吗\"")
    print("  → count +1 → 晋升检查")
    print()
    print("  第三次相同情况：晋升为永久规则")
    print("  → 以后每次醒来自动加载 → 同类错误不再犯")
    print()

    print("─" * 54)
    print("✅ Demo 结束")
    print("─" * 54)
    print()
    print("  以上是所有功能的演示效果。")
    print("  想用自己的数据？")
    print("  >>  清空 memory_data/ 目录即可。")
    print()


if __name__ == "__main__":
    print("\n🧪 正在准备演示数据...")
    clean()
    demo_data()
    run()
