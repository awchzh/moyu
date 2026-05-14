#!/usr/bin/env python3
"""
forgetting_curve.py — MOYU Memory Lifecycle (V2.0.5)

Two-stage gating:
  Stage 1 — 14-day safety window (no demotion before this threshold)
  Stage 2 — Access density trend analysis: widening intervals → demote,
            stable intervals → keep (even if past the 14-day mark)

Config (config.yaml → forgetting_curve):
  enabled: true
  demote_days: 14    → Stage 1: safety window
  archive_days: 60   → Demoted + 60 more days → archivable
  density_window: 20 → Max access timestamps to track per memory
"""

import json
import os
import statistics
from datetime import datetime, timedelta
from pathlib import Path

STORAGE = Path(os.environ.get("MOYU_STORAGE", str(Path(__file__).parent / "memory_data")))

# ── helpers ──────────────────────────────────────────────────────────────────

def _memories_path() -> str:
    return str(STORAGE / "conversation_memory.json")


def _load_memories() -> list:
    p = _memories_path()
    if os.path.exists(p):
        try:
            with open(p) as f:
                return json.load(f)
        except (json.JSONDecodeError, Exception):
            pass
    return []


def _save_memories(memories: list):
    STORAGE.mkdir(parents=True, exist_ok=True)
    with open(_memories_path(), 'w') as f:
        json.dump(memories, f, ensure_ascii=False, indent=2)


def _load_config() -> dict:
    try:
        import yaml
        cfg_path = Path(__file__).parent / "config.yaml"
        if cfg_path.exists():
            with open(cfg_path) as f:
                cfg = yaml.safe_load(f) or {}
            return cfg.get("forgetting_curve", {})
    except Exception:
        pass
    return {}


def _now() -> str:
    return datetime.now().isoformat()


def _days_since(ts_str: str) -> float:
    """Calculate days between now and a timestamp string."""
    try:
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        return (datetime.now() - dt).total_seconds() / 86400
    except Exception:
        return 0


def _days_between(ts_a: str, ts_b: str) -> float:
    """Days between two timestamp strings (positive)."""
    try:
        a = datetime.fromisoformat(ts_a.replace("Z", "+00:00"))
        b = datetime.fromisoformat(ts_b.replace("Z", "+00:00"))
        return abs((a - b).total_seconds() / 86400)
    except Exception:
        return 0


# ── Two-stage gating ─────────────────────────────────────────────────────────

def _access_density_trend(timestamps: list) -> dict:
    """
    Stage 2: analyze access interval pattern from timestamp history.

    Returns a dict with:
      trend: 'stable' | 'widening' | 'insufficient'
      median_interval_days: median gap between consecutive accesses (or None)
      detail: human-readable note
    """
    result = {"trend": "insufficient", "median_interval_days": None, "detail": "less than 2 intervals"}

    if len(timestamps) < 3:
        return result  # Need at least 3 timestamps for 2 intervals

    intervals = []
    for i in range(1, len(timestamps)):
        gap = _days_between(timestamps[i], timestamps[i - 1])
        if gap > 0:
            intervals.append(gap)

    if len(intervals) < 2:
        return result

    median_val = statistics.median(intervals)
    result["median_interval_days"] = round(median_val, 1)

    # Split into first half and second half to detect widening trend
    mid = len(intervals) // 2
    first_half = intervals[:mid]
    second_half = intervals[mid:]

    avg_first = sum(first_half) / len(first_half)
    avg_second = sum(second_half) / len(second_half)

    if avg_second > avg_first * 1.5:
        result["trend"] = "widening"
        result["detail"] = (
            f"intervals widening: {avg_first:.1f}d → {avg_second:.1f}d "
            f"(median {median_val:.1f}d)"
        )
    else:
        result["trend"] = "stable"
        result["detail"] = (
            f"intervals stable: {avg_first:.1f}d → {avg_second:.1f}d "
            f"(median {median_val:.1f}d)"
        )

    return result


# ── Core API ─────────────────────────────────────────────────────────────────

def track_access(memory_ids: list):
    """Update last_accessed, access_count, and append to access_timestamps."""
    cfg = _load_config()
    density_window = cfg.get("density_window", 20)

    memories = _load_memories()
    now = _now()
    changed = False
    for m in memories:
        if m.get("id") in memory_ids:
            m["last_accessed"] = now
            m["access_count"] = m.get("access_count", 0) + 1

            # Append to timestamp history (ring buffer capped at density_window)
            ts_list = m.get("access_timestamps", [])
            ts_list.append(now)
            if len(ts_list) > density_window:
                ts_list = ts_list[-density_window:]
            m["access_timestamps"] = ts_list

            # Remove demoted flag since it's being accessed again
            if m.pop("demoted", None) is not None:
                m.pop("demoted_reason", None)
                m.pop("demoted_by_density", None)
            changed = True
    if changed:
        _save_memories(memories)


def run(context_pressure: bool = False) -> dict:
    """
    Run the forgetting curve check on all memories (two-stage gating).

    Stage 1 — Safety window: memories within demote_days are never demoted.
    Stage 2 — Density trend: memories past the window with stable access
              patterns are kept active; widening intervals are demoted.

    Args:
        context_pressure: If True, activate demotion. If False, only
                          demote if active memories exceed a reasonable
                          budget (safe default for low-frequency users).
    Returns a report of what happened.
    """
    cfg = _load_config()
    if not cfg.get("enabled", True):
        return {"status": "disabled"}

    demote_days = cfg.get("demote_days", 14)
    archive_days = cfg.get("archive_days", 60)

    memories = _load_memories()
    active_memories = [m for m in memories if not m.get("demoted", False)]

    # ── Stage 0: skip demotion if no context pressure and few memories ──
    active_count = len(active_memories)

    if not context_pressure and active_count <= 15:
        kept_count = len([m for m in memories if m.get("demoted_by_density")])
        return {
            "status": "ok",
            "total_memories": len(memories),
            "demoted": [],
            "already_demoted": len([m for m in memories if m.get("demoted", False)]),
            "kept_by_density": kept_count,
            "kept_by_density_ids": [],
            "archivable": [],
            "demote_threshold_days": demote_days,
            "archive_threshold_days": archive_days,
            "note": "no pressure, kept all memories active",
        }

    now = _now()
    demoted = []
    kept_by_density = []
    archived = []
    re_demoted = []

    for m in memories:
        m_id = m.get("id", "?")
        is_demoted = m.get("demoted", False)
        access_ts = m.get("last_accessed") or m.get("timestamp", now)
        days = _days_since(access_ts)

        if is_demoted:
            if days >= archive_days:
                archived.append(m_id)
            else:
                re_demoted.append(m_id)
            continue

        # ── Stage 1: within safety window → skip ──
        if days < demote_days:
            continue

        # ── Stage 2: check access density trend ──
        trend = _access_density_trend(m.get("access_timestamps", []))

        if trend["trend"] == "stable":
            # Regular usage pattern — keep active despite passing the window
            m["last_checked"] = now
            kept_by_density.append(m_id)
            continue

        # Passed both gates → demote
        m["demoted"] = True
        m["demoted_reason"] = f"not accessed in {days:.0f} days"
        m["demoted_at"] = now

        if trend["trend"] == "widening":
            m["demoted_by_density"] = True
            m["demoted_reason"] += f" | access density widening: {trend['detail']}"
        else:
            m["demoted_reason"] += f" | insufficient density data ({trend['detail']})"

        demoted.append(m_id)

    if demoted or archived or kept_by_density:
        _save_memories(memories)

    return {
        "status": "ok",
        "total_memories": len(memories),
        "demoted": demoted,
        "already_demoted": len(re_demoted),
        "kept_by_density": len(kept_by_density),
        "kept_by_density_ids": kept_by_density,
        "archivable": archived,
        "demote_threshold_days": demote_days,
        "archive_threshold_days": archive_days,
    }


def summary() -> str:
    """Quick readable summary for agent messages."""
    r = run()
    parts = []
    if r.get("demoted"):
        parts.append(f"降级了 {len(r['demoted'])} 条记忆")

    kb = r.get("kept_by_density", 0)
    if kb:
        parts.append(f"密度分析保留 {kb} 条")
    if r.get("archivable"):
        parts.append(f"可归档 {len(r['archivable'])} 条")
    active = r.get("total_memories", 0) - len(r.get("demoted", []))
    parts.append(f"活跃记忆 {active} 条")
    return "，".join(parts)


def stats():
    """Terminal stats output."""
    r = run()
    print(f"\n🧠 MOYU Memory Lifecycle (two-stage gating)")
    print("=" * 55)
    print(f"  Total memories:         {r.get('total_memories', 0)}")
    print(f"  Stage 1 window:         {r.get('demote_threshold_days', '?')}d")
    print(f"  Stage 2 kept by density:{r.get('kept_by_density', 0)}")
    print(f"  Archive threshold:      {r.get('archive_threshold_days', '?')}d")
    print(f"  Freshly demoted:        {len(r.get('demoted', []))}")
    print(f"  Already demoted:        {r.get('already_demoted', 0)}")
    print(f"  Archivable:             {len(r.get('archivable', []))}")
    if r.get("demoted"):
        print(f"  Demoted IDs:            {', '.join(r['demoted'][:5])}")
    if r.get("kept_by_density_ids"):
        print(f"  Density-kept IDs:       {', '.join(r['kept_by_density_ids'][:5])}")
    print()


def demo() -> dict:
    return {
        "capability": 13,
        "title": "Forgetting Curve (V2.0.5 — Two-Stage Gating)",
        "output": """\
🧠 V2.0.5 FEATURE — Two-Stage Forgetting Curve
─────────────────────────────────────────────
  Stage 1 — 14d safety window (no memory demoted before this)
  Stage 2 — Access density trend analysis
    • Stable intervals (every 10-14d) → kept active
    • Widening intervals (1h→3d→14d) → demoted
    • Insufficient data → default demote

  [demo_01] Smart frame kickoff   → ✅ 2d  → active
  [demo_06] 张艺 hates WeChat     → ✅ 4d  → active (accessed every 12d)
  [demo_10] 用户偏好记录          → ⏳ 18d → kept by density (stable intervals)
  [demo_05] 李总 deadline         → ⏳ 32d → demoted (widening intervals)
  [demo_02] 方案讨论               → ⏳ 45d → archivable (demoted + 60d)
""",
    }


if __name__ == "__main__":
    import sys
    if "--summary" in sys.argv:
        print(summary())
    else:
        stats()
