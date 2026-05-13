#!/usr/bin/env python3
"""
knowledge_graph.py — MOYU Lightweight Knowledge Graph

Auto-extracts entities and relations from conversation to assist memory retrieval.
JSON file storage, zero database dependency.

Usage:
    python3 knowledge_graph.py extract <text>  # Extract relations
    python3 knowledge_graph.py search <query>  # Search entities
    python3 knowledge_graph.py stats           # Show statistics
"""

import json
import os
import re
from datetime import datetime
from typing import List, Dict

STORAGE_PATH = os.environ.get("MOYU_STORAGE", os.path.join(os.path.dirname(__file__), "memory_data"))

RELATION_TYPES = {
    "works_at": "works at", "uses": "uses", "lives_in": "lives in",
    "manages": "manages", "created": "created", "owns": "owns",
    "knows": "knows", "prefers": "prefers", "is_a": "is a",
    "belongs_to": "belongs to", "located_at": "located at", "develops": "develops",
    "depends_on": "depends on", "related_to": "related to",
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
    """Call the configured LLM API"""
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
                           {"role": "system", "content": "You are a precise relation extractor."},
                           {"role": "user", "content": prompt}
                       ], "temperature": 0.1}, timeout=15)
        if resp.status_code == 200:
            return resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
    except Exception:
        pass
    return ""


def _extract_fallback(text: str) -> List[Dict]:
    """Regex-based entity extraction fallback (no API key required).
    Covers common patterns: X is Y, X works at Y, X uses Y, etc."""
    triples = []
    patterns = [
        # Chinese patterns
        (r"(\S{2,8})\s*是\s*(\S{2,12})(?:[，。、！？]|$)", "is_a"),
        (r"(\S{2,8})\s*在\s*(\S{2,20})\s*(?:工作|上班|任职)", "works_at"),
        (r"(\S{2,8})\s*(?:使用|用|用的是)\s*(\S{2,20})(?:[，。、！？]|$)", "uses"),
        (r"(\S{2,8})\s*(?:喜欢|热爱|偏爱)\s*(\S{2,20})(?:[，。、！？]|$)", "prefers"),
        (r"(\S{2,8})\s*(?:属于|隶属于|归属于)\s*(\S{2,20})(?:[，。、！？]|$)", "belongs_to"),
        (r"(\S{2,8})\s*(?:开发|创建|发明)\s*(?:了)?\s*(\S{2,20})(?:[，。、！？]|$)", "created"),
        (r"(\S{2,8})\s*(?:住在|居住于|位于)\s*(\S{2,20})(?:[，。、！？]|$)", "located_at"),
        # English patterns
        (r"(\S{2,20})\s+is\s+(?:a|an)\s+(\S{2,20})", "is_a"),
        (r"(\S{2,20})\s+works?\s+(?:at|for)\s+(\S{2,30})", "works_at"),
        (r"(\S{2,20})\s+uses\s+(\S{2,30})", "uses"),
        (r"(\S{2,20})\s+(?:likes|loves|prefers)\s+(\S{2,30})", "prefers"),
        (r"(\S{2,20})\s+created\s+(\S{2,30})", "created"),
        (r"(\S{2,20})\s+(?:lives? in|is based in)\s+(\S{2,30})", "located_at"),
        (r"(\S{2,20})\s+(?:owns?|manages?)\s+(\S{2,30})", "owns"),
    ]
    for pattern, rel in patterns:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            src, tgt = m.group(1).strip(), m.group(2).strip()
            skip_words = {"他", "她", "它", "我", "你", "这个", "那个", "什么", "怎么",
                          "the", "a", "an", "this", "that", "it", "he", "she"}
            if src.lower() not in skip_words and tgt.lower() not in skip_words:
                triples.append({"source": src, "relation": rel, "target": tgt})
    return triples


def extract_entities(text: str) -> List[Dict]:
    prompt = ("Extract entity-relation triples from the following text. Format: EntityA | Relation | EntityB\n"
              "Relation types: " + ", ".join(RELATION_TYPES.keys()) +
              "\nIf none: output \"none\"\n\nText: " + text[:1500])
    reply = _call_llm(prompt)
    if not reply or reply.strip() == "none":
        return _extract_fallback(text)
    triples = []
    for line in reply.split("\n"):
        parts = [p.strip() for p in line.split("|")]
        if len(parts) == 3 and parts[2] in RELATION_TYPES:
            source, rel, target = parts
            triples.append({"source": source, "relation": rel, "target": target})
    if not triples:
        return _extract_fallback(text)
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
    print(f"\n📊 MOYU Knowledge Graph")
    print("=" * 50)
    print(f"Entities: {len(kg['entities'])} | Relations: {len(kg['relations'])}")
    top = sorted(kg["entities"].items(), key=lambda x: -x[1].get("mention_count", 0))[:5]
    for eid, data in top:
        print(f"  {data['name']} ({data.get('mention_count', 0)} appearances)")


def demo() -> dict:
    """Return demo content for moyu_demo.py discovery engine."""
    return {
        "capability": 3,
        "title": "Knowledge Graph",
        "output": """📊 3/6  DEMO
────────────────────────────────────
  Entities & relations extracted from conversation:

  Zhang Yi ──→ works at ──→ Smart Photo Frame
  Zhang Yi ──→ uses ──→ Flask
  Zhang Yi ──→ prefers ──→ Feishu Docs
  Xiao Li ──→ works at ──→ Smart Photo Frame
  Xiao Li ──→ uses ──→ Vue3
  Boss Li ──→ manages ──→ Smart Photo Frame

  Search \"Zhang Yi\" → see all his roles and preferences.
  Pure JSON file, zero database ops.""",
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: extract <text> | search <query> | stats")
        sys.exit(0)
    cmd = sys.argv[1]
    if cmd == "extract":
        print(f"Added {add_triples(' '.join(sys.argv[2:]))} relations")
    elif cmd == "search":
        for h in search(" ".join(sys.argv[2:])):
            print(f"#{h['entity']}:")
            for r in h["relations"]:
                print(f"  {r}")
    elif cmd == "stats":
        stats()
