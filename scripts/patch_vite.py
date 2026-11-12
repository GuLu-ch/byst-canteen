"""给 vite 打一个小补丁，绕过本机沙箱的 spawn EPERM。

vite 在 Windows 上第一次调用 realpath 时会执行 `net use` 来探测网络驱动器映射：

    exec("net use", { windowsHide: true }, (error, stdout) => { ... })

DSH 的文件沙箱不允许子进程以管道方式启动（Node 里表现为 `Error: spawn EPERM`），
导致 `vite build` 在加载配置阶段直接失败。这里把这次探测改成直接使用
`fs.realpathSync.native`（本地磁盘场景下行为一致），其余逻辑保持不变。

用法：
    python scripts/patch_vite.py
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CHUNK = ROOT / "frontend" / "node_modules" / "vite" / "dist" / "node" / "chunks" / "node.js"

OLD = 'exec("net use", { windowsHide: true }, (error, stdout) => {'
NEW = (
    "safeRealpathSync = fs.realpathSync.native;\n\t"
    'if (false) exec("net use", { windowsHide: true }, (error, stdout) => {'
)
MARKER = "if (false) exec(\"net use\""


def patch(path: Path) -> int:
    if not path.exists():
        print(f"[skip] 未找到 {path}（先执行 npm install）")
        return 0
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        print(f"[ok] 已打过补丁：{path}")
        return 0
    if OLD not in text:
        print(f"[skip] 未找到匹配片段，vite 版本可能已变化：{path}")
        return 0
    path.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    print(f"[ok] 补丁已应用：{path}")
    return 0


def main() -> int:
    targets = [Path(sys.argv[1])] if len(sys.argv) > 1 else [DEFAULT_CHUNK]
    for target in targets:
        patch(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
