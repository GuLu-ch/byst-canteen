"""把表格单元格插槽还原成解构写法（jsdom 下的空 scope 由 dom_check 过滤，浏览器里始终带 props）。"""

from pathlib import Path

ROOT = Path(r"D:\WorkSpace\WEB\byst\frontend\src\admin")
TARGETS = ["Reservations.vue", "FeedbackView.vue", "Users.vue"]

for name in TARGETS:
    path = ROOT / name
    text = path.read_text(encoding="utf-8")
    count = text.count('#default="{ row = {} }"')
    new = text.replace('#default="{ row = {} }"', '#default="{ row }"')
    if new != text:
        path.write_text(new, encoding="utf-8")
    print(f"{name}: 还原 {count} 处")
