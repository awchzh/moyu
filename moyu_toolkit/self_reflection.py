#!/usr/bin/env python3
"""
self_reflection.py — MOYU Self-Reflection Module (V2.0.3)

Analyzes stored memories on wake to find:
  - Contradictions: same topic, opposing viewpoints
  - Connections: recurring entities across different time spans

Pure regex + set matching, no API key required.

Usage:
    python3 self_reflection.py              # Full analysis
    python3 self_reflection.py --compact    # One-line summary
"""

import json
import os
import re
from datetime import datetime
from typing import List, Dict

STORAGE_PATH = os.environ.get("MOYU_STORAGE", os.path.join(os.path.dirname(__file__), "memory_data"))
MEMORY_FILE = os.path.join(STORAGE_PATH, "conversation_memory.json")

# Chinese sentiment word pairs for contradiction detection
_CONTRADICTION_PAIRS = [
    (r"喜欢|热爱|推荐|赞成|支持|同意|选择", r"讨厌|不喜欢|反对|不行|拒绝|不要|放弃"),
    (r"要|需要|应该|必须", r"不要|不用|不需要|别"),
    (r"好|不错|可以|没问题", r"不好|不行|有问题|不行"),
    (r"A方案|路线A|方案A", r"B方案|路线B|方案B"),
    (r"乐观|有信心|看好", r"悲观|担心|不看好|有风险"),
]

# Chinese stop words to filter out common noise
_STOP_WORDS = {"这个", "那个", "什么", "怎么", "一个", "可以", "没有", "不是", "就是",
               "我们", "你们", "他们", "自己", "因为", "所以", "但是", "如果", "还是",
               "the", "a", "an", "this", "that", "it", "is", "are", "was", "were",
               "i", "you", "he", "she", "we", "they"}

_SENTENCE_SPLIT = re.compile(r'[。！？!?.]')


def _load_memories() -> List[Dict]:
    """Load all memories from JSON file."""
    if not os.path.exists(MEMORY_FILE):
        return []
    try:
        with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def _extract_topics(summary: str) -> List[str]:
    """Extract potential topic words from a summary."""
    # Find quoted items (terms mentioned in quotes)
    topics = []
    quoted = re.findall(r'[""「」](.+?)[""「」]', summary)
    topics.extend(quoted)

    # Find capitalized proper nouns (English context)
    proper = re.findall(r'\b[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})?\b', summary)
    topics.extend(proper)

    # Find 2-4 character Chinese phrases that repeat patterns
    words = re.findall(r'[\u4e00-\u9fff]{2,8}', summary)
    for w in words:
        if w not in _STOP_WORDS and len(w) >= 2:
            topics.append(w)

    # Deduplicate
    seen = set()
    result = []
    for t in topics:
        t_lower = t.lower().strip()
        if t_lower and t_lower not in seen:
            seen.add(t_lower)
            result.append(t)
    return result[:10]


def _detect_sentiment(text: str) -> Dict[str, float]:
    """Detect positive and negative sentiment strength in text."""
    pos_score, neg_score = 0.0, 0.0
    for pos_pattern, neg_pattern in _CONTRADICTION_PAIRS:
        pos_matches = re.findall(pos_pattern, text)
        neg_matches = re.findall(neg_pattern, text)
        pos_score += len(pos_matches) * 0.3
        neg_score += len(neg_matches) * 0.3
    return {"positive": min(1.0, pos_score), "negative": min(1.0, neg_score),
            "dominant": "positive" if pos_score > neg_score else "negative" if neg_score > pos_score else "neutral"}


def find_contradictions() -> List[Dict]:
    """Find memories with conflicting sentiments on the same topic."""
    memories = _load_memories()
    if len(memories) < 2:
        return []

    # Extract topic → sentiment for each
    topic_sentiments: Dict[str, List[Dict]] = {}
    for m in memories:
        summary = m.get("summary", "")
        topics = _extract_topics(summary)
        sentiment = _detect_sentiment(summary)
        for topic in topics:
            if topic not in topic_sentiments:
                topic_sentiments[topic] = []
            topic_sentiments[topic].append({
                "id": m.get("id", ""),
                "timestamp": m.get("timestamp", ""),
                "summary": summary[:60],
                "sentiment": sentiment,
            })

    # Find topics with opposing sentiments across different timestamps
    contradictions = []
    for topic, entries in topic_sentiments.items():
        if len(entries) < 2:
            continue
        sentiments = set(e["sentiment"]["dominant"] for e in entries if e["sentiment"]["dominant"] != "neutral")
        if "positive" in sentiments and "negative" in sentiments:
            # Found a contradiction!
            pos_entries = [e for e in entries if e["sentiment"]["dominant"] == "positive"]
            neg_entries = [e for e in entries if e["sentiment"]["dominant"] == "negative"]
            # Check they're at different times (not the same moment)
            timestamps = set(e["timestamp"][:10] for e in pos_entries + neg_entries)
            if len(timestamps) >= 2:
                contradictions.append({
                    "topic": topic,
                    "positive": pos_entries,
                    "negative": neg_entries,
                })

    # Return top 3, sorted by number of conflicting entries
    contradictions.sort(key=lambda c: len(c["positive"]) + len(c["negative"]), reverse=True)
    return contradictions[:3]


def find_connections() -> List[Dict]:
    """Find recurring entities across different time spans."""
    memories = _load_memories()
    if len(memories) < 3:
        return []

    # Track which entities appear across distinct time spans
    entity_times: Dict[str, List[str]] = {}
    for m in memories:
        summary = m.get("summary", "")
        ts = m.get("timestamp", "")[:10]
        topics = _extract_topics(summary)
        for topic in topics:
            if topic not in entity_times:
                entity_times[topic] = []
            if ts not in entity_times[topic]:
                entity_times[topic].append(ts)

    # Find entities that span the widest time range
    connections = []
    for entity, dates in entity_times.items():
        if len(dates) >= 3:  # Appeared 3+ times on different days
            try:
                first = datetime.fromisoformat(min(dates))
                last = datetime.fromisoformat(max(dates))
                span_days = (last - first).days
            except Exception:
                span_days = 0
            connections.append({
                "entity": entity,
                "span_days": span_days,
                "mention_count": len(dates),
                "first_seen": min(dates),
                "last_seen": max(dates),
            })

    # Return top 3 longest-running topics
    connections.sort(key=lambda c: (c["span_days"], c["mention_count"]), reverse=True)
    return connections[:3]


def run() -> str:
    """Run full reflection analysis and return a readable summary."""
    contradictions = find_contradictions()
    connections = find_connections()

    lines = []
    if contradictions:
        lines.append("🔄 反思发现了一些记忆冲突：")
        for c in contradictions:
            pos_times = min(len(c["positive"]), 2)
            neg_times = min(len(c["negative"]), 2)
            lines.append(f"  关于【{c['topic']}】— 有 {len(c['positive'])} 条正面记录 / {len(c['negative'])} 条负面记录")

    if connections:
        lines.append("🔗 存在跨时间关联的话题：")
        for c in connections:
            lines.append(f"  {c['entity']} — 跨越 {c['span_days']} 天，被提及 {c['mention_count']} 次")

    if not lines:
        lines.append("✅ 未发现记忆冲突或跨时间关联")

    return "\n".join(lines)


def run_compact() -> str:
    """Return a one-line summary for quick wake display."""
    contradictions = find_contradictions()
    connections = find_connections()
    parts = []
    if contradictions:
        parts.append(f"{len(contradictions)} 个记忆冲突")
    if connections:
        parts.append(f"{len(connections)} 个跨时间关联")
    if not parts:
        return "✅ 反思完成，无异常"
    return "反思发现" + "、".join(parts)


def demo() -> dict:
    return {
        "capability": 7,
        "title": "Self-Reflection (V2.0.3)",
        "output": """\
🔄 反思发现了一些记忆冲突：
  关于【B方案】— 有 1 条正面记录 / 1 条负面记录
  关于【天气插件】— 有 2 条正面记录 / 1 条负面记录

🔗 存在跨时间关联的话题：
  智能相框 — 跨越 4 天，被提及 5 次
  张艺 — 跨越 2 天，被提及 3 次""",
    }


if __name__ == "__main__":
    import sys
    compact = "--compact" in sys.argv
    if compact:
        print(run_compact())
    else:
        print(run())
