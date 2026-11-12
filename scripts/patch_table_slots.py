"""给 Element Plus 表格单元格插槽加解构默认值，避免 scope 为空时整页白屏。"""

from pathlib import Path

ROOT = Path(r"D:\WorkSpace\WEB\byst\frontend\src\admin")
TARGETS = ["Reservations.vue", "FeedbackView.vue", "Users.vue"]

for name in TARGETS:
    path = ROOT / name
    text = path.read_text(encoding="utf-8")
    count = text.count('#default="{ row }"')
    new = text.replace('#default="{ row }"', '#default="{ row = {} }"')
    if new != text:
        path.write_text(new, encoding="utf-8")
    print(f"{name}: 替换 {count} 处")
