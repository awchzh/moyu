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
"""

import sys
import os
import subprocess

TOOLKIT_DIR = os.path.dirname(os.path.abspath(__file__))


def _run_module(module_name: str, args: list):
    """Run a module with given args, preserving execution context"""
    path = os.path.join(TOOLKIT_DIR, *module_name.split(".")) + ".py"
    cmd = [sys.executable, path] + args
    result = subprocess.run(cmd)
    sys.exit(result.returncode)


def _run_python(code: str):
    """Execute inline Python code with toolkit dir set"""
    # Inject TOOLKIT_DIR into the code
    injected = (
        f'import sys, os\n'
        f'__file__ = os.path.join({repr(TOOLKIT_DIR)}, "moyu.py")\n'
        f'sys.path.insert(0, {repr(TOOLKIT_DIR)})\n'
        f'{code}'
    )
    result = subprocess.run([sys.executable, "-c", injected])
    sys.exit(result.returncode)


def cmd_stats():
    """Aggregate statistics from all modules"""
    code = """
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from agent_memory import stats as mem_stats
from active_context import status as ctx_status
from learner import stats as learn_stats

print()
print("=" * 50)
print("  MOYU — Global Statistics")
print("=" * 50)
mem_stats()
ctx_status()
learn_stats()

try:
    from security import status as sec_status
    sec_status()
except ImportError:
    pass
"""
    _run_python(code)


def cmd_status():
    """Show system health check"""
    code = """
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

print("=" * 50)
print("  MOYU — System Status")
print("=" * 50)

# Check config
import yaml
cfg_path = os.path.join(os.path.dirname(__file__), "config.yaml")
if os.path.exists(cfg_path):
    with open(cfg_path) as f:
        cfg = yaml.safe_load(f) or {}
    has_key = bool(cfg.get("api", {}).get("api_key", ""))
    key_status = "✅ Configured" if has_key else "⚠️  Not set (local mode)"
    print(f"  API Key:  {key_status}")
else:
    print(f"  API Key:  ❌ config.yaml not found")

# Check storage
storage = os.environ.get("MOYU_STORAGE", os.path.join(os.path.dirname(__file__), "memory_data"))
if os.path.isdir(storage):
    files = [f for f in os.listdir(storage) if f.endswith(".json")]
    print(f"  Storage:  ✅ {len(files)} data files in {os.path.basename(storage)}/")
else:
    print(f"  Storage:  ⚠️  Not initialized (run first command to create)")

# Check security
sec_path = os.path.join(os.path.dirname(__file__), "security.py")
if os.path.exists(sec_path):
    print(f"  Security: ✅ memory_self_defense.py ready")
else:
    print(f"  Security: ⚠️  Not available")

print()
"""
    _run_python(code)


def cmd_demo():
    """Run the demo showcase"""
    demo_path = os.path.join(TOOLKIT_DIR, "moyu_demo.py")
    result = subprocess.run([sys.executable, demo_path])
    sys.exit(result.returncode)


def show_help():
    print(__doc__.strip())


COMMANDS = {
    "search":     ("agent_memory", ["search"]),
    "learn":      ("learner", ["learn"]),
    "detect":     ("learner", ["detect"]),
    "inject":     ("learner", ["inject"]),
    "signals":    ("learner", ["signals"]),
    "setup":      ("security", ["setup"]),
    "verify":     ("security", ["verify"]),
    "unlock":     ("security", ["unlock"]),
    "check":      ("defense_toolkit.integrity_checker", []),
    "init":       ("defense_toolkit.integrity_checker", ["init"]),
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("help", "--help", "-h"):
        show_help()
        sys.exit(0)

    cmd = sys.argv[1]
    rest = sys.argv[2:]

    if cmd == "stats":
        cmd_stats()
    elif cmd == "status":
        cmd_status()
    elif cmd == "demo":
        cmd_demo()
    elif cmd in COMMANDS:
        module, prefix_args = COMMANDS[cmd]
        _run_module(module, prefix_args + rest)
    else:
        print(f"Unknown command: {cmd}")
        print()
        show_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
