#!/usr/bin/env python3
"""
active_context.py — MOYU 工作记忆

解决上下文压缩后丢失"当前在做什么"的问题。
独立文件存储，不被任何压缩机制触碰。

用法：
    python3 active_context.py status        # 查看当前工作记忆
    python3 active_context.py start         # 新会话
    python3 active_context.py set task ...  # 设置任务
    python3 active_context.py add ...       # 记录关键上下文
    python3 active_context.py todo add ...  # 添加待办
    python3 active_context.py todo done ..  # 完成待办
    python3 active_context.py inject        # 获取注入格式
"""

import json
import os
from datetime import datetime

STORAGE_PATH = os.environ.get("MOYU_STORAGE", os.path.join(os.path.dirname(__file__), "memory_data"))


def _path() -> str:
    os.makedirs(STORAGE_PATH, exist_ok=True)
    return os.path.join(STORAGE_PATH, "active_context.json")


def _load() -> dict:
    p = _path()
    if os.path.exists(p):
        try:
            with open(p) as f:
                return json.load(f)
        except Exception:
            pass
    return _default()


def _save(ctx: dict):
    with open(_path(), 'w') as f:
        json.dump(ctx, f, ensure_ascii=False, indent=2)


def _default() -> dict:
    return {
        "session_start": datetime.now().isoformat(),
        "task": "",
        "contexts": [],
        "todos": [],
        "last_updated": datetime.now().isoformat()
    }


def start_session():
    _save(_default())
    print("✅ 新会话已启动")


def set_task(task: str):
    ctx = _load()
    ctx["task"] = task
    ctx["last_updated"] = datetime.now().isoformat()
    _save(ctx)
    print(f"✅ 任务: {task}")


def add_context(text: str):
    ctx = _load()
    ctx["contexts"].append({"text": text[:200], "timestamp": datetime.now().isoformat()})
    if len(ctx["contexts"]) > 5:
        ctx["contexts"] = ctx["contexts"][-5:]
    ctx["last_updated"] = datetime.now().isoformat()
    _save(ctx)
    print(f"✅ 上下文已记录")


class Todo:
    @staticmethod
    def add(text: str):
        ctx = _load()
        ctx["todos"].append({"id": len(ctx["todos"]) + 1, "text": text[:200], "done": False,
                             "created": datetime.now().isoformat()})
        ctx["last_updated"] = datetime.now().isoformat()
        _save(ctx)
        print(f"✅ 待办: {text[:60]}")

    @staticmethod
    def done(tid: str):
        ctx = _load()
        for t in ctx["todos"]:
            if str(t["id"]) == tid or t["text"].startswith(tid):
                t["done"] = True
                t["completed_at"] = datetime.now().isoformat()
        ctx["last_updated"] = datetime.now().isoformat()
        _save(ctx)
        print(f"✅ 已完成: {tid}")


def format_for_injection() -> str:
    ctx = _load()
    lines = ["## [工作记忆 — 当前会话上下文]\n"]
    if ctx["task"]:
        lines.append(f"**当前任务：** {ctx['task']}\n")
    if ctx["contexts"]:
        lines.append("**关键信息：**")
        for c in ctx["contexts"]:
            ts = c.get("timestamp", "")[:16]
            lines.append(f"- [{ts}] {c['text']}")
        lines.append("")
    pending = [t for t in ctx["todos"] if not t["done"]]
    if pending:
        lines.append("**待办：**")
        for t in pending:
            lines.append(f"- [ ] {t['text']}")
        lines.append("")
    lines.append(f"*开始于 {ctx['session_start'][:19]}，最近更新 {ctx['last_updated'][:19]}*")
    return "\n".join(lines)


def status():
    ctx = _load()
    print(f"\n📋 工作记忆")
    print("=" * 50)
    print(f"会话: {ctx['session_start'][:19]}")
    print(f"任务: {ctx['task'] or '无'}")
    print(f"上下文: {len(ctx['contexts'])} 条")
    print(f"待办: {len(ctx['todos'])} 项")
    for t in ctx['todos']:
        m = "✅" if t["done"] else "⬜"
        print(f"  {m} {t['text'][:80]}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: status | start | set task | add | todo")
        sys.exit(0)
    cmd = sys.argv[1]
    if cmd == "status": status()
    elif cmd == "start": start_session()
    elif cmd == "set" and len(sys.argv) >= 4 and sys.argv[2] == "task":
        set_task(" ".join(sys.argv[3:]))
    elif cmd == "add":
        add_context(" ".join(sys.argv[2:]))
    elif cmd == "todo" and len(sys.argv) >= 4:
        Todo.add(" ".join(sys.argv[3:])) if sys.argv[2] == "add" else Todo.done(" ".join(sys.argv[3:]))
    elif cmd == "inject":
        print(format_for_injection())
