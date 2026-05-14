#!/usr/bin/env python3
"""
moyu — MOYU unified CLI entry point

Usage:
    moyu search <query>     Search memories
    moyu learn <text>       Learn from correction
    moyu stats              Show all statistics
    moyu status             Show system status
    moyu setup              Set up security password
    moyu verify <type> [desc]  Verify dangerous operation
    moyu unlock             Unlock security system
    moyu check              Check file integrity
    moyu inject             Get rules for injection
    moyu signals            View active trigger words
    moyu demo               Show all capabilities
    moyu compress           Show compression status
    moyu compress --now     Force manual compression
    moyu forget             Show memory lifecycle (forgetting curve)
    moyu update             Check for updates
    moyu update now         Download & apply update
"""

import sys
import os

TOOLKIT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLKIT_DIR)


def _import(name):
    import importlib.util
    path = os.path.join(TOOLKIT_DIR, *name.split(".")) + ".py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def cmd_stats():
    mem = _import("agent_memory")
    ctx = _import("active_context")
    lrn = _import("learner")
    print()
    print("=" * 50)
    print("  MOYU — Global Statistics")
    print("=" * 50)
    mem.stats()
    ctx.status()
    lrn.stats()
    try:
        sec = _import("security")
        sec.status()
    except Exception:
        pass
    print()


def cmd_audit():
    """Security audit — one-report summary of all defense layers."""
    print()
    print("=" * 52)
    print("  🛡️  MOYU Security Audit")
    print("=" * 52)

    # Layer 1: Memory Self-Defense (pre-operation)
    sec_mod = _import("security")
    import json as _json
    import os as _os
    # Read security config directly (avoid sec.status() which prints)
    sec_cfg_path = _os.path.join(TOOLKIT_DIR, "memory_data", "security_config.json")
    has_pw = False
    failures = 0
    if _os.path.exists(sec_cfg_path):
        try:
            with open(sec_cfg_path) as _f:
                _cfg = _json.load(_f)
                has_pw = bool(_cfg.get("safe_word_hash", ""))
        except Exception:
            pass
    # Count failures
    fail_path = _os.path.join(TOOLKIT_DIR, "memory_data", "security_failures.json")
    if _os.path.exists(fail_path):
        try:
            with open(fail_path) as _f:
                failures = len(_json.load(_f))
        except Exception:
            pass
    print(f"\n  ⚡ Layer 1 — Pre-operation (security.py)")
    if has_pw:
        print(f"     ✅  Password set")
    else:
        print(f"     ⚠️   Password not set — run `moyu setup`")
    if failures:
        print(f"     ⚠️   {failures} recent failed attempts")

    # Layer 2: Integrity Check (on-wake detection)
    ic = _import("defense_toolkit.integrity_checker")
    import os as _os
    storage_base = _os.environ.get("MOYU_STORAGE",
                                    _os.path.join(TOOLKIT_DIR, "memory_data"))
    manifest_path = _os.path.join(storage_base, "manifest.json")
    backup_dir = _os.path.join(storage_base, "backups")
    has_manifest = _os.path.exists(manifest_path)
    print(f"\n  🔍 Layer 2 — On-wake detection (integrity_checker.py)")
    if has_manifest:
        print(f"     ✅  Manifest initialized")
        # Count daily backups
        if _os.path.isdir(backup_dir):
            backups = [f for f in _os.listdir(backup_dir) if f.startswith("daily_")]
            print(f"     ✅  {len(backups)} daily backup(s) available")
        else:
            print(f"     ⚠️   No backups yet (will be created on next wake)")
    else:
        print(f"     ⚠️   Manifest not initialized — run `moyu init`")

    # Layer 3: Auto Recovery (post-tamper)
    print(f"\n  🔄 Layer 3 — Post-tamper recovery")
    if has_manifest and _os.path.isdir(backup_dir):
        backups = [f for f in _os.listdir(backup_dir) if f.startswith("daily_")]
        if backups:
            dates = set()
            for f in backups:
                parts = f.split("_", 2)
                if len(parts) >= 2:
                    dates.add(parts[1])
            print(f"     ✅  Auto-recovery ready — {len(dates)} days of backup available")
        else:
            print(f"     ⚠️   No backup data yet")
    else:
        print(f"     —  Not ready (run `moyu init` first)")

    print()
    print(f"  {'=' * 52}")
    all_good = has_pw and has_manifest
    print(f"  {'✅ All defense layers operational' if all_good else '⚠️  Some layers need attention'}")
    print()


def cmd_status():
    import yaml
    print()
    print("=" * 50)
    print("  MOYU — System Status")
    print("=" * 50)
    cfg_path = os.path.join(TOOLKIT_DIR, "config.yaml")
    if os.path.exists(cfg_path):
        with open(cfg_path) as f:
            cfg = yaml.safe_load(f) or {}
        print(f"  API Key:  {'✅ Configured' if cfg.get('api', {}).get('api_key', '') else '⚠️ Not set (local mode)'}")
    else:
        print("  API Key:  ❌ config.yaml not found")
    storage = os.environ.get("MOYU_STORAGE", os.path.join(TOOLKIT_DIR, "memory_data"))
    if os.path.isdir(storage):
        files = [f for f in os.listdir(storage) if f.endswith(".json")]
        print(f"  Storage:  ✅ {len(files)} data files")
    else:
        print("  Storage:  ⚠️ Not initialized")
    print(f"  Security: {'✅ ready' if os.path.exists(os.path.join(TOOLKIT_DIR, 'security.py')) else '⚠️ Not available'}")
    print()
    # Defense chain visualization
    print(f"  {'─' * 48}")
    print(f"  🛡️  Defense Chain")
    print(f"  {'─' * 48}")
    # Layer 1 — Pre-op (read config directly, avoid sec.status() which prints)
    import json as _json2
    import os as _os2
    _sec_cfg = {}
    _scp = _os2.path.join(TOOLKIT_DIR, "memory_data", "security_config.json")
    if _os2.path.exists(_scp):
        try:
            with open(_scp) as _f:
                _sec_cfg = _json2.load(_f)
        except Exception:
            pass
    _pw_set = bool(_sec_cfg.get("safe_word_hash", ""))
    print(f"  ⚡ Pre-op:   {'✅ Password Set' if _pw_set else '⚠️ No Password'}  (moyu setup)")
    # Layer 2 — On-wake
    _sto = _os2.environ.get("MOYU_STORAGE", _os2.path.join(TOOLKIT_DIR, "memory_data"))
    _has_man = _os2.path.exists(_os2.path.join(_sto, "manifest.json"))
    print(f"  🔍 On-wake:  {'✅ Manifest Ready' if _has_man else '⚠️ Not Initialized'}  (moyu init)")
    # Layer 3 — Post-tamper
    _bak = _os2.path.join(_sto, "backups")
    _has_bak = _os2.path.isdir(_bak) and any(f.startswith("daily_") for f in _os2.listdir(_bak)) if _os2.path.isdir(_bak) else False
    print(f"  🔄 Post:     {'✅ Recovery Ready' if _has_bak else '⚠️ No Backups Yet'}")
    print(f"  {'─' * 48}")
    print()


def cmd_demo():
    """Safely import and run moyu_demo."""
    import importlib.util
    demo_path = os.path.join(TOOLKIT_DIR, "moyu_demo.py")
    spec = importlib.util.spec_from_file_location("moyu_demo", demo_path)
    if spec and spec.loader:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "run"):
            mod.run()


CMD_TABLE = {
    "search":     lambda args: _handle_search(args),
    "stats":      lambda args: cmd_stats(),
    "status":     lambda args: cmd_status(),
    "learn":      lambda args: _call_func("learner", "learn", [" ".join(args)]),
    "detect":     lambda args: _call_func("learner", "detect", [" ".join(args)]),
    "inject":     lambda args: print(_import("learner").get_rules_for_injection()),
    "signals":    lambda args: _call_func("learner", "signals", args),
    "setup":      lambda args: _import("security").setup(),
    "verify":     lambda args: _verify_op(args),
    "unlock":     lambda args: _import("security").unlock(),
    "check":      lambda args: _call_func("defense_toolkit.integrity_checker", "verify", args),
    "init":       lambda args: _call_func("defense_toolkit.integrity_checker", "init_manifest", args),
    "compress":   lambda args: _compress(args),
    "context":    lambda args: print(_import("context_manager").status_line()),
    "forget":     lambda args: _forget(args),
    "lifecycle":  lambda args: _forget(args),  # alias
    "bridge":     lambda args: _import("session_bridge").status(),
    "update":     lambda args: _update(args),
    "demo":       lambda args: cmd_demo(),
    "reflect":    lambda args: _call_func("self_reflection", "run", []),
    "audit":      lambda args: cmd_audit(),
    "kb":         lambda args: _kb_handler(args),
}


def _call_func(module, func, args):
    m = _import(module)
    fn = getattr(m, func, None)
    if fn:
        fn(*args)


def _verify_op(args):
    sec = _import("security")
    if len(args) < 1:
        print("Usage: moyu verify <op_type> [context]")
        return
    op = args[0]
    ctx = " ".join(args[1:])
    result = sec.verify_operation(op, ctx)
    print("✅ Allowed" if result else "❌ Denied")


def _handle_search(args):
    if not args:
        print("Usage: moyu search <query>")
        return
    query = " ".join(args)
    mem = _import("agent_memory")
    try:
        results = mem.search(query)
    except Exception:
        results = []
    if not results:
        print("No results found.")
        return
    print(f"\nSearch results for: {query}")
    print("=" * 40)
    for r in results:
        print(f"  [{r['timestamp'][:10]}] {r['summary'][:80]}")
        print(f"  Score: {r.get('score', 0)}")
        print()


def _compress(args):
    cm = _import("context_manager")
    if "--now" in args:
        ctx = _import("active_context")
        lrn = _import("learner")
        wm = ctx.format_for_injection()
        rules = lrn.get_rules_for_injection()
        result, report = cm.build_injection(working_memory=wm, behavioral_rules=rules)
        msg = cm.last_report_message()
        print(f"🚚 Manual compression triggered")
        print(f"  {msg}" if msg else f"  No compression needed ({report['usage_pct']}% of budget)")
        print()
    else:
        cm.stats()


def _forget(args):
    """Handle forget command — check forgetting curve status."""
    fc = _import("forgetting_curve")
    if "--summary" in args:
        print(fc.summary())
    else:
        fc.stats()


def _update(args):
    """Handle update command — check and apply updates."""
    up = _import("updater")
    if "--dry" in args or "check" in args:
        info = up.check()
        if "error" in info:
            print(f"Error: {info['error']}")
        else:
            print(f"Current: v{info['current']} → Latest: v{info['latest']}")
            print(f"Update available: {info['is_newer']}")
    elif "now" in args or "apply" in args:
        result = up.update()
        print(result["message"])
    else:
        up.stats()


def _kb_handler(args):
    """Handle knowledge base commands: search, list, index, read."""
    kb = _import("knowledge_base")
    if not args or args[0] in ("help", "--help"):
        print("moyu kb commands:")
        print("  moyu kb index              Rebuild keyword index")
        print("  moyu kb search  <query>    Search knowledge files")
        print("  moyu kb list               List all knowledge files")
        print("  moyu kb read   <file>      Read a knowledge file")
        return
    subcmd = args[0]
    subargs = args[1:]
    if subcmd == "index":
        idx = kb.index()
        print(f"Indexed {idx['total']} knowledge files")
    elif subcmd == "search":
        query = " ".join(subargs)
        if not query:
            print("Usage: moyu kb search <query>")
            return
        results = kb.search(query)
        if results:
            print(f"\n📚 Knowledge Base results for: {query}")
            print("=" * 40)
            for r in results:
                print(f"  📄 {r['filename']} (score: {r['score']})")
                print(f"     path: {r['path']}")
                if r.get("triggers"):
                    print(f"     triggers: {', '.join(r['triggers'][:5])}")
                print()
        else:
            print(f"No results for '{query}'. Try `moyu kb index` first, or add files to knowledge/")
    elif subcmd == "list":
        kb.stats()
    elif subcmd == "read":
        fname = " ".join(subargs)
        content = kb.read(fname)
        if content:
            print(content)
        else:
            print(f"File not found. Try `moyu kb list` to see available files.")
    else:
        print(f"Unknown kb subcommand: {subcmd}")
        print("Usage: moyu kb {index|search|list|read}")


def show_help():
    print(__doc__.strip())


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("help", "--help", "-h"):
        show_help()
        sys.exit(0)

    cmd = sys.argv[1]
    rest = sys.argv[2:]

    # ── Silent integrity check + daily backup ──
    # Runs verify() on every moyu command. Checks hashes, triggers daily backup.
    # User only sees output if tampering is detected or manifest is missing.
    if cmd not in ("setup", "init", "audit", "check", "help", "--help", "-h"):
        try:
            ic = _import("defense_toolkit.integrity_checker")
            ic.verify()
        except Exception:
            pass

    # ── Security initialization prompt (silent) ──
    if cmd not in ("setup", "init", "audit", "help", "--help", "-h"):
        try:
            sec = _import("security")
            sec_info = sec.status()
            ic_module = _import("defense_toolkit.integrity_checker")
            import os as _os3
            sto = _os3.environ.get("MOYU_STORAGE",
                                    _os3.path.join(TOOLKIT_DIR, "memory_data"))
            man = _os3.path.join(sto, "manifest.json")
            if not sec_info.get("password_set", False) or not _os3.path.exists(man):
                print()
                print("  ⚡ Tip: Protect your memory layer!")
                if not sec_info.get("password_set", False):
                    print("     Run `moyu setup` to set a memory self-defense password")
                if not _os3.path.exists(man):
                    print("     Run `moyu init` to initialize integrity verification")
                print()
        except Exception:
            pass

    handler = CMD_TABLE.get(cmd)
    if handler:
        handler(rest)
    else:
        print(f"Unknown command: {cmd}")
        print()
        show_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
