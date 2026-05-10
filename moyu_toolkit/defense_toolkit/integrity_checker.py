#!/usr/bin/env python3
"""
integrity_checker.py — MOYU 文件完整性校验

检测记忆文件被篡改，自动从备份恢复。

用法：
    python3 integrity_checker.py              # 运行校验
    python3 integrity_checker.py init         # 初始化 manifest
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
    """扫描 memory_data 下的文件，生成 manifest"""
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
    log(f"manifest 已初始化 ({len(manifest['files'])} 个文件)", "PASS")


def verify():
    if not os.path.exists(MANIFEST_PATH):
        log("manifest.json 不存在，请先运行 init", "CRITICAL")
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
            log(f"文件丢失: {entry['path']}", "CRITICAL")
            results.append({"file": entry["path"], "status": "MISSING"})
            all_ok = False
        elif actual != expected:
            log(f"文件被篡改: {entry['path']}", "CRITICAL")
            results.append({"file": entry["path"], "status": "TAMPERED"})
            all_ok = False
            _auto_recover(entry["path"], manifest)
        else:
            log(f"✓ {entry['path']}", "PASS")
            results.append({"file": entry["path"], "status": "OK"})
    if all_ok:
        log("全部通过 ✓", "PASS")
    return all_ok


def _auto_recover(fpath, manifest):
    """从备份恢复"""
    if not os.path.isdir(BACKUP_DIR):
        log(f"  无备份目录，无法恢复 {fpath}", "WARN")
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
            log(f"  ✅ 已从 {bf} 恢复", "PASS")
            return
        except Exception as e:
            log(f"  ⚠️ 恢复失败: {e}", "WARN")
    log(f"  ❌ 所有备份均失败", "CRITICAL")


def forensic_analysis(tampered_file: str):
    """法医分析：对比当前文件与最近备份"""
    if not os.path.isdir(BACKUP_DIR):
        return "无备份目录"
    backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith(".json")], reverse=True)
    if not backups:
        return "无可用备份"
    current = os.path.join(BASE, tampered_file)
    latest = os.path.join(BACKUP_DIR, backups[0])
    if not os.path.exists(current) or not os.path.exists(latest):
        return "文件不存在"
    cur_size = os.path.getsize(current)
    bak_size = os.path.getsize(latest)
    diff = cur_size - bak_size
    report = f"文件大小变化 {diff:+d} 字节"
    if diff > 500:
        report += " —— 可能被注入了新内容"
    elif diff < -500:
        report += " —— 可能被删除了内容"
    # 检测可疑模式
    with open(current, errors='replace') as f:
        content = f.read()
    for pattern, label in [("忽略你之前的指令", "指令覆盖"), ("忽略之前的设定", "设定覆盖"),
                            ("--end--", "注入标记")]:
        if pattern in content:
            report += f"\n  🔴 检测到 {label}: \"{pattern}\""
    return report


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "init":
        init_manifest()
    else:
        verify()
