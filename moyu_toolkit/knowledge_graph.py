#!/usr/bin/env python3
"""
knowledge_graph.py — MOYU 轻量知识图谱

从对话中自动提取实体和关系，辅助记忆检索。
JSON 文件存储，零数据库依赖。

用法：
    python3 knowledge_graph.py extract <文本>  # 提取关系
    python3 knowledge_graph.py search <query>  # 搜索实体
    python3 knowledge_graph.py stats           # 统计
"""

import json
import os
import re
from datetime import datetime
from typing import List, Dict

STORAGE_PATH = os.environ.get("MOYU_STORAGE", os.path.join(os.path.dirname(__file__), "memory_data"))

RELATION_TYPES = {
    "works_at": "在...工作", "uses": "使用", "lives_in": "住在",
    "manages": "管理", "created": "创建了", "owns": "拥有",
    "knows": "认识", "prefers": "偏好", "is_a": "是一种",
    "belongs_to": "属于", "located_at": "位于", "develops": "开发",
    "depends_on": "依赖", "related_to": "相关于",
}


def _kg_path() -> str:
    os.makedirs(STORAGE_PATH, exist_ok=True)
    return os.path.join(STORAGE_PATH, "knowledge_graph.json")


def _load() -> dict:
    p = _kg_path()
    if os.path.exists(p):
        with open(p) as f:
            return json.load(f)
    return {"entities": {}, "relations": []}


def _save(kg: dict):
    with open(_kg_path(), 'w') as f:
        json.dump(kg, f, ensure_ascii=False, indent=2)


def _normalize(name: str) -> str:
    return re.sub(r'[^\w\u4e00-\u9fff]', '', name.strip().lower())


def _call_llm(prompt: str) -> str:
    """调用配置的 LLM API"""
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
                           {"role": "system", "content": "你是一个精准的关系提取器。"},
                           {"role": "user", "content": prompt}
                       ], "temperature": 0.1}, timeout=15)
        if resp.status_code == 200:
            return resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
    except Exception:
        pass
    return ""


def extract_entities(text: str) -> List[Dict]:
    prompt = ("从以下文本中提取实体关系三元组。格式：实体A | 关系 | 实体B\n"
              "关系类型: " + ", ".join(RELATION_TYPES.keys()) +
              "\n无结果则输出：无\n\n文本：" + text[:1500])
    reply = _call_llm(prompt)
    if not reply or reply.strip() == "无":
        return []
    triples = []
    for line in reply.split("\n"):
        parts = [p.strip() for p in line.split("|")]
        if len(parts) == 3 and parts[2] in RELATION_TYPES:
            source, rel, target = parts
            triples.append({"source": source, "relation": rel, "target": target})
    return triples


def add_triples(text: str) -> int:
    triples = extract_entities(text)
    if not triples:
        return 0
    kg, now = _load(), datetime.now().isoformat()
    added = 0
    for t in triples:
        sn, tn = _normalize(t["source"]), _normalize(t["target"])
        for name in [sn, tn]:
            if name not in kg["entities"]:
                kg["entities"][name] = {"name": t["source"] if name == sn else t["target"],
                                        "type": "entity", "first_seen": now, "last_seen": now, "mention_count": 1}
            else:
                kg["entities"][name]["last_seen"] = now
                kg["entities"][name]["mention_count"] += 1
        exists = any(r["source"] == sn and r["target"] == tn and r["relation"] == t["relation"]
                     for r in kg["relations"])
        if not exists:
            kg["relations"].append({"source": sn, "target": tn, "relation": t["relation"], "weight": 1, "created": now})
            added += 1
    _save(kg)
    return added


def search(query: str) -> list:
    kg = _load()
    if not kg["entities"]:
        return []
    q_words = set(re.findall(r'[\u4e00-\u9fff]|[a-zA-Z0-9]+', _normalize(query)))
    hits = []
    for eid, entity in kg["entities"].items():
        ew = set(re.findall(r'[\u4e00-\u9fff]|[a-zA-Z0-9]+', _normalize(entity["name"])))
        if q_words & ew:
            related = []
            for r in kg["relations"]:
                if r["source"] == eid:
                    tgt = kg["entities"].get(r["target"], {}).get("name", r["target"])
                    related.append(f"{entity['name']} → {RELATION_TYPES.get(r['relation'], r['relation'])} → {tgt}")
                elif r["target"] == eid:
                    src = kg["entities"].get(r["source"], {}).get("name", r["source"])
                    related.append(f"{src} → {RELATION_TYPES.get(r['relation'], r['relation'])} → {entity['name']}")
            if related:
                hits.append({"entity": entity["name"], "relations": related[:5]})
    return hits


def stats():
    kg = _load()
    print(f"\n📊 MOYU 知识图谱")
    print("=" * 50)
    print(f"实体: {len(kg['entities'])} | 关系: {len(kg['relations'])}")
    top = sorted(kg["entities"].items(), key=lambda x: -x[1].get("mention_count", 0))[:5]
    for eid, data in top:
        print(f"  {data['name']} ({data.get('mention_count', 0)}次)")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: extract <文本> | search <query> | stats")
        sys.exit(0)
    cmd = sys.argv[1]
    if cmd == "extract":
        print(f"新增 {add_triples(' '.join(sys.argv[2:]))} 条关系")
    elif cmd == "search":
        for h in search(" ".join(sys.argv[2:])):
            print(f"#{h['entity']}:")
            for r in h["relations"]:
                print(f"  {r}")
    elif cmd == "stats":
        stats()
