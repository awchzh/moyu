#!/usr/bin/env python3
"""
agent_memory.py — MOYU Vector Memory Engine

Core Features:
- TEMPR multi-strategy retrieval (semantic + BM25 keyword + time decay)
- Automatic memory indexing
- Duplicate prevention mechanism

Usage:
    python3 agent_memory.py index      # Batch index all memories
    python3 agent_memory.py search q   # Search relevant memories
    python3 agent_memory.py stats      # Show index status
"""

import json
import os
import math
import re
import collections
import hashlib
import numpy as np
from datetime import datetime
from typing import List, Dict, Optional, Tuple

# ==================== Configuration ====================

# Default path, can be overridden via MOYU_STORAGE environment variable
STORAGE_PATH = os.environ.get("MOYU_STORAGE", os.path.join(os.path.dirname(__file__), "memory_data"))

# TEMPR retrieval weights
TEMPR_WEIGHTS = {"semantic": 0.5, "keyword": 0.3, "recency": 0.2}
SEMANTIC_FALLBACK_THRESHOLD = 0.1

# n-gram fallback configuration
NGRAM_N = 3
NGRAM_DIM = 256
MAX_TEXT_LENGTH = 512


def _storage_path(*parts: str) -> str:
    """Get storage path"""
    path = os.path.join(STORAGE_PATH, *parts)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


def _load_config() -> dict:
    """Load config.yaml (if exists)"""
    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    if os.path.exists(config_path):
        try:
            import yaml
            with open(config_path) as f:
                return yaml.safe_load(f) or {}
        except Exception:
            pass
    return {}


def _get_embedding_api() -> Tuple[str, str, str]:
    """Get embedding API configuration"""
    config = _load_config()
    api_cfg = config.get("api", {})
    base_url = api_cfg.get("base_url", "https://api.openai.com/v1").rstrip("/")
    api_key = api_cfg.get("api_key", "") or os.environ.get("MOYU_API_KEY", "")
    model = api_cfg.get("embedding_model", "text-embedding-3-small")
    chat_url = base_url + "/embeddings"
    return api_key, chat_url, model


def _get_chat_api() -> Tuple[str, str, str]:
    """Get chat API configuration"""
    config = _load_config()
    api_cfg = config.get("api", {})
    base_url = api_cfg.get("base_url", "https://api.openai.com/v1").rstrip("/")
    api_key = api_cfg.get("api_key", "") or os.environ.get("MOYU_API_KEY", "")
    model = api_cfg.get("chat_model", "gpt-4o-mini")
    chat_url = base_url + "/chat/completions"
    return api_key, chat_url, model


# ==================== Vector Operations ====================

def cosine_similarity(vec1: list, vec2: list) -> float:
    a, b = np.array(vec1), np.array(vec2)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-10))


# ==================== TEMPR Multi-Strategy Retrieval ====================

def _bm25_score(query_words: list, doc_words: list,
                avg_len: float, doc_len: float,
                doc_freq: dict, total_docs: int,
                k1=1.5, b=0.75) -> float:
    score = 0.0
    for qw in query_words:
        if qw not in doc_freq or doc_freq[qw] == 0:
            continue
        idf = math.log((total_docs - doc_freq[qw] + 0.5) / (doc_freq[qw] + 0.5) + 1.0)
        tf = doc_words.count(qw)
        score += idf * ((tf * (k1 + 1)) / (tf + k1 * (1 - b + b * doc_len / avg_len)))
    return score


def _build_bm25_index(summaries: list) -> tuple:
    tokenized, word_df, total_len = [], collections.defaultdict(int), 0
    for s in summaries:
        words = re.findall(r'[\u4e00-\u9fff]|[a-zA-Z0-9]+', s.lower())
        tokenized.append(words)
        total_len += len(words)
        for w in set(words):
            word_df[w] += 1
    avg_len = total_len / max(len(summaries), 1)
    return tokenized, dict(word_df), avg_len


def _tempr_score(query: str, summary: str, timestamp: str,
                 semantic: float, bm25_tok: list,
                 bm25_df: dict, bm25_avg: float, total: int) -> float:
    ws = TEMPR_WEIGHTS
    if semantic < SEMANTIC_FALLBACK_THRESHOLD:
        ws = {**ws, "semantic": ws["semantic"] * 0.3}
    q_words = re.findall(r'[\u4e00-\u9fff]|[a-zA-Z0-9]+', query.lower())
    bm25 = _bm25_score(q_words, bm25_tok, bm25_avg, len(bm25_tok), bm25_df, total)
    bm25 = min(1.0, bm25 / 5.0)
    try:
        mt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        age = max(0, (datetime.now() - mt).total_seconds() / 3600)
        recency = max(0.1, 1.0 - age / (30 * 24))
    except Exception:
        recency = 0.5
    return ws["semantic"] * semantic + ws["keyword"] * bm25 + ws["recency"] * recency


# ==================== Embedding ====================

def _get_ngram_embedding(text: str) -> list:
    text = text[:MAX_TEXT_LENGTH]
    ngrams = set()
    for i in range(len(text) - NGRAM_N + 1):
        ngrams.add(abs(hash(text[i:i+NGRAM_N])) % NGRAM_DIM)
    vec = [0.0] * NGRAM_DIM
    for idx in ngrams:
        vec[idx] = 1.0
    return vec


def get_embedding(text: str, is_query: bool = False) -> Optional[list]:
    """Get text embedding, auto-fallback to n-gram when API unavailable"""
    text = text[:MAX_TEXT_LENGTH]
    api_key, url, model = _get_embedding_api()
    if api_key:
        try:
            import requests
            resp = requests.post(
                url,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"input": text, "model": model},
                timeout=15
            )
            if resp.status_code == 200:
                data = resp.json()
                vec = data.get("data", [{}])[0].get("embedding")
                if vec:
                    return vec
        except Exception:
            pass
    return _get_ngram_embedding(text)


# ==================== Memory Index Management ====================

def _load_index() -> dict:
    path = _storage_path("vector_index.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {"vectors": []}


def _save_index(index: dict):
    path = _storage_path("vector_index.json")
    with open(path, 'w') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


def _load_memories() -> list:
    path = _storage_path("conversation_memory.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return []


def _save_memories(memories: list):
    path = _storage_path("conversation_memory.json")
    with open(path, 'w') as f:
        json.dump(memories, f, ensure_ascii=False, indent=2)


def add_memory(summary: str, source: str = "user",
               metadata: dict = None) -> Optional[dict]:
    """Add a memory entry (auto-dedup + index)"""
    content_hash = hashlib.sha256(summary.encode()).hexdigest()[:16]
    memories = _load_memories()
    for m in memories:
        if m.get("content_hash") == content_hash:
            return None  # Duplicate, skip
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    entry = {
        "id": f"mem_{ts}",
        "timestamp": datetime.now().isoformat(),
        "source": source,
        "summary": summary[:500],
        "content_hash": content_hash,
        "metadata": metadata or {}
    }
    memories.append(entry)
    _save_memories(memories)
    _add_to_index(entry["id"], entry["summary"], entry["timestamp"], source)
    return entry


def _add_to_index(mid: str, summary: str, ts: str, source: str):
    idx = _load_index()
    for v in idx["vectors"]:
        if v["memory_id"] == mid:
            return
    vec = get_embedding(summary)
    if vec is None:
        return
    idx["vectors"].append({
        "memory_id": mid, "timestamp": ts,
        "source": source, "summary": summary[:80], "vector": vec
    })
    _save_index(idx)


def batch_index():
    """Batch index all unindexed memories"""
    memories = _load_memories()
    idx = _load_index()
    indexed = {v["memory_id"] for v in idx["vectors"]}
    to_idx = [m for m in memories if m["id"] not in indexed]
    for m in to_idx:
        _add_to_index(m["id"], m.get("summary", ""), m.get("timestamp", ""), m.get("source", ""))
    print(f"✅ Indexed {len(to_idx)}/{len(memories)} memories")


def search(query: str, top_k: int = 5) -> list:
    """TEMPR multi-strategy retrieval"""
    idx = _load_index()
    if not idx["vectors"]:
        return []
    memories = _load_memories()
    mem_map = {m["id"]: m for m in memories}
    summaries = [mem_map.get(v["memory_id"], {}).get("summary", v.get("summary", ""))
                 for v in idx["vectors"]]
    bm25_tok, bm25_df, bm25_avg = _build_bm25_index(summaries)
    total = len(summaries)
    q_vec = get_embedding(query, is_query=True)
    scored = []
    for i, entry in enumerate(idx["vectors"]):
        sem = cosine_similarity(q_vec, entry["vector"]) if q_vec else 0.0
        raw = _tempr_score(query, summaries[i], entry.get("timestamp", ""),
                           sem, bm25_tok[i], bm25_df, bm25_avg, total)
        scored.append((raw, entry))
    scored.sort(key=lambda x: -x[0])
    results = []
    for score, entry in scored[:top_k]:
        results.append({
            "memory_id": entry["memory_id"],
            "timestamp": entry["timestamp"],
            "source": entry["source"],
            "summary": mem_map.get(entry["memory_id"], {}).get("summary", entry.get("summary", "")),
            "score": round(score, 4)
        })
    return results


def stats():
    idx = _load_index()
    vecs = idx["vectors"]
    print(f"\n📊 MOYU Vector Memory")
    print("=" * 50)
    print(f"Indexed: {len(vecs)} entries")
    if vecs:
        srcs = collections.Counter(v.get("source", "unknown") for v in vecs)
        print(f"\nSource distribution:")
        for s, c in srcs.most_common():
            print(f"  {s}: {c} entries")


def demo() -> dict:
    """Return demo content for moyu_demo.py discovery engine."""
    return {
        "capability": 1,
        "title": "TEMPR Multi-Strategy Retrieval",
        "output": """🔍 1/6  DEMO
────────────────────────────────────
  You said: \"上次开会说了什么方案\"

  ⭐ Hit [Discussion] Confirmed A/B roadmap for smart photo frame
  ⭐ Hit [Meeting] Discussed pricing and feature priorities
  ⭐ Hit [Decision] Team decided to go with MVP first

  Even if your search words don't match the original text exactly,
  TEMPR (semantic + BM25 keyword + time-weighted) still finds it.""",
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: index | search <query> | stats")
        sys.exit(0)
    cmd = sys.argv[1]
    if cmd == "index":
        batch_index()
    elif cmd == "search":
        q = " ".join(sys.argv[2:])
        for r in search(q):
            print(f"[{r['score']:.4f}] {r['timestamp'][:10]} [{r['source']}]")
            print(f"  {r['summary'][:100]}\n")
    elif cmd == "stats":
        stats()
