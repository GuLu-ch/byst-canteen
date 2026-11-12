# -*- coding: utf-8 -*-
"""v7: 给管理端 8 个页面的 api.* 调用补第三参 'admin'。只处理 .vue 内 api.get/post/put/del/blob/upload(...) 调用，
要求：调用以 api.<method>( 开头，且括号内参数个数 = 该方法原有参数个数（未传 kind）。"""
from __future__ import annotations

import re
from pathlib import Path

BASE = Path(r"D:\WorkSpace\WEB\byst\frontend\src\admin")
FILES = [
    "Votes.vue", "Menus.vue", "Reviews.vue", "Dashboard.vue",
    "Users.vue", "Reservations.vue", "SettingsView.vue", "FeedbackView.vue",
]

# 每个 api 方法的「业务参数」个数（不含 kind）：get=2(path,params) post=2(path,body) put=2 del=1 blob=2 upload=2
ARITY = {"get": 2, "post": 2, "put": 2, "del": 1, "blob": 2, "upload": 2}

CALL_RE = re.compile(r"\bapi\.(get|post|put|del|blob|upload)\(", re.M)

def split_args(src: str, open_idx: int) -> tuple[str, int] | None:
    """从 api.<method>( 的 open_idx 开始取完整括号内容。返回 (参数串, 右括号后一位置) 或 None。"""
    depth = 0
    i = open_idx
    in_str = None
    while i < len(src):
        ch = src[i]
        if in_str:
            if ch == "\\":
                i += 2
                continue
            if ch == in_str:
                in_str = None
        else:
            if ch in ("'", '"', "`"):
                in_str = ch
            elif ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    return src[open_idx + 1 : i], i + 1
        i += 1
    return None

def count_top_level_args(args: str) -> int:
    """按顶层逗号数参数（忽略括号/引号内的逗号）。空串=0 个参数。"""
    if not args.strip():
        return 0
    depth = 0
    in_str = None
    count = 1
    i = 0
    while i < len(args):
        ch = args[i]
        if in_str:
            if ch == "\\":
                i += 2
                continue
            if ch == in_str:
                in_str = None
        else:
            if ch in ("'", '"', "`"):
                in_str = ch
            elif ch in "([{":
                depth += 1
            elif ch in ")]}":
                depth -= 1
            elif ch == "," and depth == 0:
                count += 1
        i += 1
    return count

changed_total = 0
for name in FILES:
    path = BASE / name
    src = path.read_text(encoding="utf-8")
    out = []
    pos = 0
    changed = 0
    for m in CALL_RE.finditer(src):
        method = m.group(1)
        start = m.end()  # '(' 位置
        parsed = split_args(src, start)
        if parsed is None:
            continue
        args, after = parsed
        n = count_top_level_args(args)
        arity = ARITY[method]
        # 多行调用里的参数串保留原样；只在参数个数 == arity 时补 'admin'
        out.append(src[pos:start])
        if n == arity:
            stripped = args.rstrip()
            # 已经有 kind（不该发生，n==arity 时最后一个参数是业务参数）
            out.append(args[: len(args) - len(stripped)] if args != stripped else args)
            # 判断是否多行调用：参数串里含换行
            if "\n" in stripped:
                out.append(stripped + ",\n  'admin'" + (")" if False else ""))
                # 直接在最后一个右括号前插入
                out.pop()
                out.append(stripped + ", 'admin'")
            else:
                out.append(stripped + ", 'admin'")
            changed += 1
        else:
            out.append(args)
        pos = after
    out.append(src[pos:])
    new = "".join(out)
    if changed:
        path.write_text(new, encoding="utf-8")
        print(f"{name}: {changed} calls patched")
        changed_total += changed
    else:
        print(f"{name}: no change")

print(f"\ntotal patched: {changed_total}")
