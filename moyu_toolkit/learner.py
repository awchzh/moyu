#!/usr/bin/env python3
"""
learner.py — MOYU 学习信号模块

从用户纠正中自动学习经验，同类错误不再犯第二次。
同一类错3次后晋升为永久行为规则。

用法：
    python3 learner.py detect <文本>  # 检测纠正信号
    python3 learner.py learn <文本>   # 从纠正中学习
    python3 learner.py stats          # 统计
    python3 learner.py inject         # 获取注入格式
"""

import json
import os
import re
from datetime import datetime

STORAGE_PATH = os.environ.get("MOYU_STORAGE", os.path.join(os.path.dirname(__file__), "memory_data"))

# 默认纠正信号触发词（可在 config.yaml 中覆盖）
DEFAULT_SIGNALS = [
    "不是", "不对", "错了", "应该是", "不要",
    "记住", "我告诉过你", "我说过", "别", "别再",
    "你又", "还说",
]

IGNORE_PATTERNS = [r"他\w*不", r"我不(知道|确定)", r"不太好"]


def _load_config() -> dict:
    import yaml
    cfg_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path) as f:
                return yaml.safe_load(f) or {}
        except Exception:
            pass
    return {}


def _correction_signals() -> list:
    cfg = _load_config()
    return cfg.get("learner", {}).get("correction_signals", DEFAULT_SIGNALS)


def _call_llm(prompt: str) -> str:
    import yaml, requests as rq
    cfg_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    if not os.path.exists(cfg_path):
        return ""
    with open(cfg_path) as f:
        cfg = yaml.safe_load(f) or {}
    api_cfg = cfg.get("api", {})
    key = api_cfg.get("api_key", "") or os.environ.get("MOYU_API_KEY", "")
    if not key:
        return ""
    url = api_cfg.get("base_url", "https://api.openai.com/v1").rstrip("/") + "/chat/completions"
    model = api_cfg.get("chat_model", "gpt-4o-mini")
    try:
        resp = rq.post(url, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                       json={"model": model, "messages": [
                           {"role": "system", "content": "你是一个经验提取器。"},
                           {"role": "user", "content": prompt}
                       ], "temperature": 0.1}, timeout=15)
        if resp.status_code == 200:
            return resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
    except Exception:
        pass
    return ""


def detect_corrections(text: str) -> list:
    if not text:
        return []
    signals = _correction_signals()
    last_msg = text.split("\n")[-1][:200]
    hits = []
    for sig in signals:
        if sig in last_msg:
            ignored = any(re.search(p, last_msg) for p in IGNORE_PATTERNS)
            if not ignored:
                hits.append(f"[{sig}] {last_msg[:100]}")
    return hits


def learn(text: str) -> bool:
    """从纠正文本中学习"""
    lessons = _load_lessons()
    corrections = _load_corrections()
    lesson_text = _extract_lesson(text)
    if not lesson_text:
        return False
    existing = next((l for l in lessons["lessons"]
                     if _similar(l.get("lesson", ""), lesson_text)), None)
    now = datetime.now().isoformat()
    if existing:
        existing["count"] += 1
        existing["last_triggered"] = now
        if existing["count"] >= 3 and not existing.get("promoted"):
            existing["promoted"] = True
            print(f"  ⬆️ 晋升规则: {existing['lesson'][:60]}")
    else:
        for c in corrections:
            if text[:50] in c:
                return False
        lessons["lessons"].append({
            "id": f"LSN-{len(lessons['lessons'])+1:03d}",
            "lesson": lesson_text, "count": 1, "created": now,
            "last_triggered": now, "promoted": False
        })
        print(f"  📝 新经验: {lesson_text[:60]}")
    _save_lessons(lessons)
    entry = f"## {now[:16]}\n\n{text}\n"
    corrections.append(entry)
    _save_corrections(corrections)
    return True


def _extract_lesson(text: str) -> str:
    reply = _call_llm(f"用户纠正了AI。提取一条经验教训：{text[:500]}")
    if reply and reply != "无":
        return reply[:100]
    patterns = [
        r"不要(.+?)[。，]?", r"别(.+?)[。，]?", r"应该(.+?)[。，]?",
        r"记住(.+?)[。，]?", r"正确的做法是(.+?)[。，]?"
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            return f"用户纠正：{m.group(1)[:60]}"
    return ""


def _similar(a: str, b: str) -> bool:
    wa = set(re.findall(r'[\u4e00-\u9fff]', a))
    wb = set(re.findall(r'[\u4e00-\u9fff]', b))
    if not wa or not wb:
        return False
    return len(wa & wb) / max(len(wa), len(wb)) > 0.3


def _path(kind: str) -> str:
    os.makedirs(STORAGE_PATH, exist_ok=True)
    return os.path.join(STORAGE_PATH, kind)


def _load_lessons() -> dict:
    p = _path("lessons.json")
    if os.path.exists(p):
        try:
            with open(p) as f:
                return json.load(f)
        except Exception:
            pass
    return {"lessons": []}


def _save_lessons(d):
    with open(_path("lessons.json"), 'w') as f:
        json.dump(d, f, ensure_ascii=False, indent=2)


def _load_corrections() -> list:
    p = _path("corrections.md")
    if os.path.exists(p):
        with open(p) as f:
            return [e.strip() for e in f.read().split("---") if e.strip()]
    return []


def _save_corrections(entries):
    lines = ["# 纠正记录", "---"] + [e + "\n---" for e in entries[-50:]]
    with open(_path("corrections.md"), 'w') as f:
        f.write("\n".join(lines))


def get_rules_for_injection() -> str:
    lessons = _load_lessons()
    promoted = [l for l in lessons["lessons"] if l.get("promoted")]
    if promoted:
        lines = ["### ✅ 行为规则（来自用户纠正）"]
        for l in promoted:
            lines.append(f"- {l['lesson']}")
        return "\n".join(lines)
    pending = [l for l in lessons["lessons"] if l.get("count", 0) >= 2 and not l.get("promoted")]
    if pending:
        lines = ["### ⚠️ 待确认规则"]
        for l in pending:
            lines.append(f"- {l['lesson']}（{l['count']}次）")
        return "\n".join(lines)
    return ""


def stats():
    lessons = _load_lessons()
    all_l = lessons["lessons"]
    promoted = [l for l in all_l if l.get("promoted")]
    print(f"\n📚 MOYU 学习者")
    print("=" * 50)
    print(f"总经验: {len(all_l)} | 规则: {len(promoted)}")
    for l in promoted:
        print(f"  ✅ [{l['count']}次] {l['lesson'][:60]}")
    for l in all_l:
        if not l.get("promoted"):
            print(f"  ⏳ [{l['count']}次] {l['lesson'][:60]}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: detect | learn | stats | inject")
        sys.exit(0)
    cmd = sys.argv[1]
    if cmd == "detect":
        for h in detect_corrections(" ".join(sys.argv[2:])):
            print(f"  {h}")
    elif cmd == "learn":
        learn(" ".join(sys.argv[2:]))
        stats()
    elif cmd == "stats":
        stats()
    elif cmd == "inject":
        print(get_rules_for_injection())
