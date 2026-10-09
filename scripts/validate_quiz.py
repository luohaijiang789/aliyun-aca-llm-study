#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACA 题库全量质检脚本
校验项：
 1. 题量与题型配比（官方铁律：50 = 单35 + 多15；M1 6/3, M2 7/3, M3 8/3, M4 6/2, M5 4/2, M6 4/2）
 2. 每道题必须恰好 4 个选项 A/B/C/D（禁 E/F）
 3. 单选题答案唯一；多选题答案 >= 2 个且不含重复
 4. 解析中 ✅ 标记集合 == 答案集合
 5. 四段式要素齐全（答案/考点/官方依据/解析/举一反三/易错提醒/我错了吗）
 6. 题头考点编号规范（M?-K??，用 / 分隔，禁止 ~ 范围）
 7. 考点编号必须存在于官方考点映射表
 8. 禁用词：插件（官方全文 0 次）
用法：python3 scripts/validate_quiz.py
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUIZ_DIR = os.path.join(ROOT, "quiz")

# 官方铁律：(单选, 多选)
OFFICIAL = {
    "01": (6, 3), "02": (7, 3), "03": (8, 3),
    "04": (6, 2), "05": (4, 2), "06": (4, 2),
}

BANNED = ["插件"]

errors = []
warns = []


def err(ctx, msg):
    errors.append(f"[ERROR] {ctx}: {msg}")


def warn(ctx, msg):
    warns.append(f"[WARN ] {ctx}: {msg}")


def load_knowledge_codes():
    """从模块资料文档加载所有合法考点编号（唯一契约：105 个）"""
    codes = set()
    mods = os.path.join(ROOT, "docs", "modules")
    if os.path.isdir(mods):
        for fn in os.listdir(mods):
            if fn.endswith(".md"):
                with open(os.path.join(mods, fn), encoding="utf-8") as f:
                    for m in re.finditer(r"\b(M\d-K\d{2})\b", f.read()):
                        codes.add(m.group(1))
    return codes


def split_questions(text):
    """按 ### Q00x 切分"""
    parts = re.split(r"^### (Q\d+)\b.*$", text, flags=re.M)
    out = []
    for i in range(1, len(parts), 2):
        out.append((parts[i], parts[i + 1]))
    return out


def main():
    all_codes = load_knowledge_codes()
    total_single = total_multi = 0
    # 该校验器只负责 01～06 六个正式模块题库。07/08 等专项练习采用
    # 不同题头和解析结构，不应被当作正式 50 题题库校验。
    files = sorted(f for f in os.listdir(QUIZ_DIR)
                   if f.endswith(".md") and f[:2] in OFFICIAL)

    for fn in files:
        mid = fn[:2]
        path = os.path.join(QUIZ_DIR, fn)
        with open(path, encoding="utf-8") as f:
            text = f.read()

        qs = split_questions(text)
        if not qs:
            err(fn, "未解析到任何题目（题头格式异常）")
            continue

        n_single = n_multi = 0
        for qid, body in qs:
            ctx = f"{fn} {qid}"
            # 题型
            header_m = re.search(r"^### (Q\d+) (\[[^\]]+\]) (\[[ABC]\])(.*)$",
                                 text[text.index(f"### {qid} "):], flags=re.M)
            header_line = ""
            for line in text.splitlines():
                if line.startswith(f"### {qid} "):
                    header_line = line
                    break
            if "多选" in header_line:
                qtype = "多选"
                n_multi += 1
            else:
                qtype = "单选"
                n_single += 1

            # 6. 题头规范
            m = re.match(r"^### (Q\d+) \[(.+?)\] \[([ABC])\](.*)$", header_line)
            if not m:
                err(ctx, f"题头格式不规范：{header_line!r}")
                continue
            code_part, cred, rest = m.group(2), m.group(3), m.group(4)
            if "~" in code_part:
                err(ctx, f"题头考点编号禁止使用 ~ 范围写法：{code_part}")
            if "⚠" in rest:
                pass  # 待核实标记，合法
            # 7. 考点编号合法性
            for c in re.findall(r"\b(M\d-K\d{2})\b", code_part):
                if all_codes and c not in all_codes:
                    warn(ctx, f"考点编号不在映射表：{c}")
            if cred == "C" and "⚠" not in rest and "待核实" not in rest:
                warn(ctx, "[C] 级推断题未标注 ⚠️待核实")

            # 2. 选项
            opts = re.findall(r"^- ([A-F])\.", body, flags=re.M)
            if opts != ["A", "B", "C", "D"]:
                err(ctx, f"选项异常，实际为 {opts}（必须恰好 A/B/C/D 四项）")

            # 3. 答案
            am = re.search(r"^\*\*答案\*\*[：:]\s*(.+)$", body, flags=re.M)
            if not am:
                err(ctx, "缺少 **答案** 行")
                continue
            ans_raw = am.group(1).strip()
            ans = re.findall(r"[A-F]", ans_raw.split("|")[0].split("（")[0])
            # 排除形如 "ABD" 被当单词处理的情况
            ans = re.findall(r"[A-F]", "".join(re.findall(r"[A-F]", ans_raw.split("|")[0])))
            if not ans:
                err(ctx, f"答案无法解析：{ans_raw!r}")
                continue
            if len(set(ans)) != len(ans):
                err(ctx, f"答案含重复字母：{ans}")
            if any(a not in "ABCD" for a in ans):
                err(ctx, f"答案含超范围字母（E/F）：{ans}")
            if qtype == "单选" and len(ans) != 1:
                err(ctx, f"单选题答案应唯一，实际 {ans}")
            if qtype == "多选" and len(ans) < 2:
                err(ctx, f"多选题答案应 >= 2 个，实际 {ans}")

            # 4. 解析 ✅ 集合
            checks = re.findall(r"^- ([A-F])\s*✅", body, flags=re.M)
            if sorted(set(checks)) != sorted(set(ans)):
                err(ctx, f"解析 ✅ 集合 {sorted(set(checks))} != 答案 {sorted(set(ans))}")

            # 5. 四段式
            for key in ["**考点**", "**官方依据**", "**解析**", "**举一反三**", "**易错提醒**"]:
                if key not in body:
                    err(ctx, f"缺少 {key}")
            if "我错了吗" not in body:
                warn(ctx, "缺少「我错了吗」打卡项")

            # 8. 禁用词（跳过「用词禁令」说明行本身）
            for line in body.splitlines():
                if any(x in line for x in ("0 次", "用词禁令", "禁用词", "不再使用")):
                    continue
                for b in BANNED:
                    if b in line:
                        err(ctx, f"出现官方禁用词「{b}」：{line.strip()[:60]}")

        exp_s, exp_m = OFFICIAL.get(mid, (None, None))
        if exp_s is not None:
            if (n_single, n_multi) != (exp_s, exp_m):
                err(fn, f"题量不符：实际 单{n_single}+多{n_multi}，官方要求 单{exp_s}+多{exp_m}")
        total_single += n_single
        total_multi += n_multi
        print(f"  {fn}: 单选 {n_single} + 多选 {n_multi} = {n_single + n_multi}")

    print(f"\n总计：单选 {total_single} + 多选 {total_multi} = {total_single + total_multi}"
          f"（官方：35 + 15 = 50）")
    if (total_single, total_multi) != (35, 15):
        err("总计", f"总题量不符：单{total_single}+多{total_multi}")

    print(f"\n{'=' * 60}")
    print(f"错误 {len(errors)} 条 / 警告 {len(warns)} 条")
    print("=" * 60)
    for w in warns:
        print(w)
    for e in errors:
        print(e)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
