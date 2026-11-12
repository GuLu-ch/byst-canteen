"""用 Playwright 驱动本机 Chrome，对移动端与管理端逐页截图并收集前端报错。

用法（后端已在 127.0.0.1:8000 运行时）：
    python scripts/ui_check.py            # 全部页面
    python scripts/ui_check.py mobile     # 只跑移动端
    python scripts/ui_check.py admin      # 只跑管理端

截图输出到 docs/screenshots/，控制台错误打印在终端。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

for _key in list(os.environ):
    if "proxy" in _key.lower():
        os.environ.pop(_key, None)

import httpx  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = "http://127.0.0.1:8000"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "screenshots"

EMPLOYEE = "13800000012"
ADMIN = "13800000000"
COOK = "13800000001"
PASSWORD = "123456"

MOBILE_PAGES = [
    ("/", "m01-home"),
    ("/reserve", "m02-reserve"),
    ("/menu", "m03-week-menu"),
    ("/review", "m04-review"),
    ("/vote", "m05-vote"),
    ("/feedback", "m06-feedback"),
    ("/me", "m07-profile"),
]

ADMIN_PAGES = [
    ("/admin", "a01-dashboard"),
    ("/admin/reservations", "a02-reservations"),
    ("/admin/menus", "a03-menus"),
    ("/admin/feedback", "a04-feedback"),
    ("/admin/reviews", "a05-reviews"),
    ("/admin/votes", "a06-votes"),
    ("/admin/users", "a07-users"),
    ("/admin/settings", "a08-settings"),
]


def login(phone: str) -> dict:
    response = httpx.post(
        f"{BASE}/api/auth/login",
        json={"phone": phone, "password": PASSWORD},
        timeout=20,
        trust_env=False,
    )
    response.raise_for_status()
    return response.json()


def run(pages, token: str, viewport: dict, mobile: bool) -> int:
    problems: list[str] = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            executable_path=CHROME,
            headless=True,
            args=["--no-sandbox", "--disable-breakpad", "--disable-crash-reporter", "--hide-scrollbars"],
        )
        context = browser.new_context(
            viewport=viewport,
            device_scale_factor=2,
            is_mobile=mobile,
            has_touch=mobile,
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
        )
        context.add_init_script(f"try {{ localStorage.setItem('byst_token', {token!r}); }} catch (e) {{}}")
        page = context.new_page()
        page.on(
            "console",
            lambda msg: problems.append(f"[console.{msg.type}] {msg.text}")
            if msg.type in ("error", "warning")
            else None,
        )
        page.on("pageerror", lambda err: problems.append(f"[pageerror] {err}"))

        for path, name in pages:
            before = len(problems)
            page.goto(BASE + path, wait_until="networkidle", timeout=45000)
            page.wait_for_timeout(1500)
            target = OUT / f"{name}.png"
            page.screenshot(path=str(target), full_page=False)
            text = page.evaluate("document.body.innerText").replace("\n", " ")[:110]
            status = "OK " if len(problems) == before else "ERR"
            print(f"{status} {path:26s} -> {target.name:22s} | {text}")
        context.close()
        browser.close()

    if problems:
        print("\n--- 前端报错 / 警告 ---")
        for item in dict.fromkeys(problems):
            print(" ", item)
    return len(problems)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    scope = sys.argv[1] if len(sys.argv) > 1 else "all"
    total = 0
    if scope in ("all", "mobile"):
        token = login(EMPLOYEE)["token"]
        total += run(MOBILE_PAGES, token, {"width": 390, "height": 844}, True)
    if scope in ("all", "admin", "staff"):
        token = login(ADMIN)["token"]
        total += run(ADMIN_PAGES, token, {"width": 1440, "height": 900}, False)
    print(f"\n共 {total} 条控制台错误/警告")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
