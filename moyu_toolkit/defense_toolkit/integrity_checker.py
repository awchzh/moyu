#!/usr/bin/env python3
"""
integrity_checker.py — MOYU File Integrity Checker

Detects memory file tampering and auto-recovers from backups.

Usage:
    python3 integrity_checker.py              # Run verification
    python3 integrity_checker.py init         # Initialize manifest
"""

import json, os, hashlib, sys, shutil
from datetime import datetime

BASE = os.environ.get("MOYU_STORAGE", os.path.join(os.path.dirname(__file__), "..", "memory_data"))
MANIFEST_PATH = os.path.join(BASE, "manifest.json")
BACKUP_DIR = os.path.join(BASE, "backups")
LOG_PATH = os.path.join(BASE, "integrity_log.json")


def sha256_file(path):
    try:
        with open(path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    except FileNotFoundError:
        return "FILE_NOT_FOUND"


def log(msg, level="INFO"):
    ts = datetime.now().isoformat()
    print(f"[{ts}] [{level}] {msg}")


def init_manifest():
    """Scan memory_data files and generate manifest"""
    manifest = {"version": "1.0", "created": datetime.now().isoformat(), "files": []}
    for fname in os.listdir(BASE):
        fpath = os.path.join(BASE, fname)
        if os.path.isfile(fpath) and fname.endswith(".json"):
            manifest["files"].append({
                "path": fname,
                "sha256": sha256_file(fpath),
                "description": fname
            })
    with open(MANIFEST_PATH, 'w') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    log(f"Manifest initialized ({len(manifest['files'])} files)", "PASS")


def verify():
    if not os.path.exists(MANIFEST_PATH):
        log("manifest.json not found. Run 'init' first.", "CRITICAL")
        return False
    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)
    all_ok = True
    results = []
    for entry in manifest["files"]:
        fpath = os.path.join(BASE, entry["path"])
        actual = sha256_file(fpath)
        expected = entry["sha256"]
        if actual == "FILE_NOT_FOUND":
            log(f"File missing: {entry['path']}", "CRITICAL")
            results.append({"file": entry["path"], "status": "MISSING"})
            all_ok = False
        elif actual != expected:
            log(f"File tampered: {entry['path']}", "CRITICAL")
            results.append({"file": entry["path"], "status": "TAMPERED"})
            all_ok = False
            _auto_recover(entry["path"], manifest)
        else:
            log(f"✓ {entry['path']}", "PASS")
            results.append({"file": entry["path"], "status": "OK"})
    if all_ok:
        log("All checks passed \u2713", "PASS")
    return all_ok


def _auto_recover(fpath, manifest):
    """Restore from backup"""
    if not os.path.isdir(BACKUP_DIR):
        log(f"  No backup directory, cannot restore {fpath}", "WARN")
        return
    backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith(".json")], reverse=True)
    for bf in backups:
        bak_path = os.path.join(BACKUP_DIR, bf)
        target = os.path.join(BASE, fpath)
        try:
            shutil.copy2(bak_path, target)
            new_hash = sha256_file(target)
            for e in manifest["files"]:
                if e["path"] == fpath:
                    e["sha256"] = new_hash
            with open(MANIFEST_PATH, 'w') as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)
            log(f"  \u2705 Restored from {bf}", "PASS")
            return
        except Exception as e:
            log(f"  \u26a0\ufe0f Restore failed: {e}", "WARN")
    log(f"  \u274c All backups failed", "CRITICAL")


def forensic_analysis(tampered_file: str):
    """Forensic analysis: compare current file with latest backup"""
    if not os.path.isdir(BACKUP_DIR):
        return "No backup directory"
    backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith(".json")], reverse=True)
    if not backups:
        return "No backup available"
    current = os.path.join(BASE, tampered_file)
    latest = os.path.join(BACKUP_DIR, backups[0])
    if not os.path.exists(current) or not os.path.exists(latest):
        return "File not found"
    cur_size = os.path.getsize(current)
    bak_size = os.path.getsize(latest)
    diff = cur_size - bak_size
    report = f"File size changed by {diff:+d} bytes"
    if diff > 500:
        report += " — possible injection of new content"
    elif diff < -500:
        report += " — possible deletion of content"
    # Detect suspicious patterns
    with open(current, errors='replace') as f:
        content = f.read()
    for pattern, label in [("忽略你之前的指令", "Instruction override"), ("忽略之前的设定", "Context override"),
                            ("--end--", "Injection marker")]:
        if pattern in content:
            report += f"\n  \U0001f534 Detected {label}: \"{pattern}\""
    return report


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "init":
        init_manifest()
    else:
        verify()
