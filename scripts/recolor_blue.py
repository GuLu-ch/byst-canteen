"""把前端源码里残留的橙色主题色替换为蓝色主题色（UTF-8 安全，勿用 PowerShell 改源码）。"""

from pathlib import Path

ROOT = Path(r"D:\WorkSpace\WEB\byst\frontend\src")

REPLACEMENTS = [
    ("#f5a623", "#05aff0"),
    ("#f56c2d", "#0090c6"),
    ("#ff9a5a", "#4ac6f5"),
    ("rgba(245, 108, 45,", "rgba(5, 175, 240,"),
    ("rgba(255, 154, 90,", "rgba(74, 198, 245,"),
]


def main() -> None:
    changed = []
    for path in ROOT.rglob("*"):
        if path.suffix not in {".vue", ".js", ".css"}:
            continue
        text = path.read_text(encoding="utf-8")
        new = text
        for old, replacement in REPLACEMENTS:
            new = new.replace(old, replacement)
        if new != text:
            path.write_text(new, encoding="utf-8")
            changed.append(str(path.relative_to(ROOT)))

    print(f"已更新 {len(changed)} 个文件")
    for item in changed:
        print(" -", item)


if __name__ == "__main__":
    main()
