#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""术语统一：全库「六选一」→「五选一」（官方原文口径：五项手段 + 保留人工确认兜底分支）

用法：
    python3 scripts/unify_terminology.py --dry-run   # 只报数，不写盘
    python3 scripts/unify_terminology.py             # 执行替换
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET_DIRS = ["docs", "quiz", "practice", "progress"]
SRC = "六选一"
DST = "五选一"

dry = "--dry-run" in sys.argv
total = 0
touched = []

for d in TARGET_DIRS:
    base = os.path.join(ROOT, d)
    if not os.path.isdir(base):
        continue
    for dirpath, _, filenames in os.walk(base):
        for fn in filenames:
            if not fn.endswith(".md"):
                continue
            path = os.path.join(dirpath, fn)
            with open(path, encoding="utf-8") as f:
                text = f.read()
            n = text.count(SRC)
            if n == 0:
                continue
            total += n
            touched.append((os.path.relpath(path, ROOT), n))
            if not dry:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text.replace(SRC, DST))

print(f"{'【预演】' if dry else '【已执行】'}共替换 {total} 处「{SRC}」→「{DST}」")
for p, n in sorted(touched):
    print(f"  {n:>2} 处  {p}")

# 复核
if not dry:
    left = 0
    for d in TARGET_DIRS:
        base = os.path.join(ROOT, d)
        if not os.path.isdir(base):
            continue
        for dirpath, _, filenames in os.walk(base):
            for fn in filenames:
                if fn.endswith(".md"):
                    with open(os.path.join(dirpath, fn), encoding="utf-8") as f:
                        left += f.read().count(SRC)
    print(f"\n复核：剩余「{SRC}」= {left} 处（应为 0）")
