"""通过 Chrome DevTools Protocol 逐页截图 + 收集前端报错。

为什么不用 Playwright：本机沙箱禁止带管道 stdio 启动子进程（WinError 5 / EPERM），
playwright 启动 driver 与浏览器都会失败；而 PowerShell 的 Start-Process 可以正常拉起
Chrome，于是这里直接用 CDP（websocket）驱动浏览器。

前置：后端运行在 127.0.0.1:8000。
用法：
    python scripts/cdp_shots.py            # 移动端 + 管理端
    python scripts/cdp_shots.py mobile
    python scripts/cdp_shots.py admin
截图输出：docs/screenshots/*.png
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

for _key in list(os.environ):
    if "proxy" in _key.lower():
        os.environ.pop(_key, None)

import httpx  # noqa: E402
import websocket  # noqa: E402

BASE = "http://127.0.0.1:8000"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT = 9222
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "screenshots"
PROFILE = ROOT / ".tmp" / "chrome-cdp"

EMPLOYEE = "13800000012"
ADMIN = "13800000000"
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


def http_json(path: str, method: str = "GET"):
    request = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}", method=method)
    with urllib.request.urlopen(request, timeout=10) as response:
        body = response.read().decode("utf-8")
    return json.loads(body) if body.strip().startswith(("{", "[")) else body


def ensure_chrome() -> None:
    try:
        http_json("/json/version")
        return
    except Exception:
        pass
    PROFILE.mkdir(parents=True, exist_ok=True)
    subprocess.Popen(
        [
            CHROME,
            "--headless=new",
            "--no-sandbox",
            "--disable-gpu",
            "--disable-breakpad",
            "--disable-crash-reporter",
            "--hide-scrollbars",
            "--force-device-scale-factor=2",
            f"--remote-debugging-port={PORT}",
            "--remote-allow-origins=*",
            f"--user-data-dir={PROFILE}",
            "about:blank",
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(40):
        time.sleep(0.5)
        try:
            http_json("/json/version")
            return
        except Exception:
            continue
    raise RuntimeError("Chrome 未能启动")


class Page:
    def __init__(self) -> None:
        target = http_json("/json/new?about:blank", method="PUT")
        self.ws = websocket.create_connection(target["webSocketDebuggerUrl"], timeout=60)
        self._id = 0
        self.events: list[dict] = []
        self.send("Page.enable")
        self.send("Runtime.enable")
        self.send("Log.enable")

    def send(self, method: str, **params):
        self._id += 1
        self.ws.send(json.dumps({"id": self._id, "method": method, "params": params}))
        while True:
            message = json.loads(self.ws.recv())
            if message.get("id") == self._id:
                if "error" in message:
                    raise RuntimeError(f"{method} 失败：{message['error']}")
                return message.get("result", {})
            if "method" in message:
                self.events.append(message)

    def drain(self) -> list[dict]:
        self.ws.settimeout(0.2)
        try:
            while True:
                message = json.loads(self.ws.recv())
                if "method" in message:
                    self.events.append(message)
        except Exception:
            pass
        finally:
            self.ws.settimeout(60)
        events, self.events = self.events, []
        return events

    def viewport(self, width: int, height: int, mobile: bool) -> None:
        self.send(
            "Emulation.setDeviceMetricsOverride",
            width=width,
            height=height,
            deviceScaleFactor=2,
            mobile=mobile,
        )

    def goto(self, url: str, extra_wait: float = 2.2) -> None:
        self.send("Page.navigate", url=url)
        time.sleep(extra_wait)

    def evaluate(self, expression: str):
        result = self.send(
            "Runtime.evaluate", expression=expression, returnByValue=True, awaitPromise=True
        )
        return result.get("result", {}).get("value")

    def screenshot(self, path: Path, full_page: bool = False) -> None:
        params = {"format": "png"}
        if full_page:
            metrics = self.send("Page.getLayoutMetrics")
            size = metrics.get("cssContentSize") or metrics.get("contentSize")
            params["captureBeyondViewport"] = True
            params["clip"] = {
                "x": 0,
                "y": 0,
                "width": size["width"],
                "height": min(size["height"], 2400),
                "scale": 1,
            }
        data = self.send("Page.captureScreenshot", **params)["data"]
        import base64

        path.write_bytes(base64.b64decode(data))

    def close(self) -> None:
        try:
            self.ws.close()
        except Exception:
            pass


def collect_errors(events: list[dict]) -> list[str]:
    problems: list[str] = []
    for event in events:
        method = event.get("method")
        params = event.get("params", {})
        if method == "Runtime.exceptionThrown":
            detail = params.get("exceptionDetails", {})
            text = detail.get("exception", {}).get("description") or detail.get("text")
            problems.append(f"[exception] {text}")
        elif method == "Runtime.consoleAPICalled" and params.get("type") in ("error", "warning"):
            args = params.get("args", [])
            text = " ".join(str(a.get("value", a.get("description", ""))) for a in args)
            problems.append(f"[console.{params['type']}] {text[:300]}")
        elif method == "Log.entryAdded":
            entry = params.get("entry", {})
            if entry.get("level") in ("error", "warning"):
                problems.append(f"[log.{entry['level']}] {entry.get('text', '')[:300]} {entry.get('url', '')}")
    return problems


def login(phone: str) -> str:
    response = httpx.post(
        f"{BASE}/api/auth/login",
        json={"phone": phone, "password": PASSWORD},
        timeout=20,
        trust_env=False,
    )
    response.raise_for_status()
    return response.json()["token"]


def run(pages, token: str, width: int, height: int, mobile: bool, tag: str) -> int:
    ensure_chrome()
    page = Page()
    page.viewport(width, height, mobile)
    page.goto(f"{BASE}/login", extra_wait=1.5)
    page.evaluate(f"localStorage.setItem('byst_token', {json.dumps(token)})")
    page.drain()

    total = 0
    for path, name in pages:
        page.goto(BASE + path, extra_wait=0.4)
        time.sleep(2.0)
        problems = collect_errors(page.drain())
        target = OUT / f"{name}.png"
        page.screenshot(target)
        text = (page.evaluate("document.body.innerText") or "").replace("\n", " ")[:100]
        total += len(problems)
        print(f"{'ERR' if problems else 'OK '} {path:24s} -> {target.name:22s} | {text}")
        for item in dict.fromkeys(problems):
            print(f"      {item}")
    page.close()
    return total


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    scope = sys.argv[1] if len(sys.argv) > 1 else "all"
    total = 0
    if scope in ("all", "mobile"):
        total += run(MOBILE_PAGES, login(EMPLOYEE), 390, 844, True, "mobile")
    if scope in ("all", "admin", "staff"):
        total += run(ADMIN_PAGES, login(ADMIN), 1440, 900, False, "admin")
    print(f"\n共 {total} 条前端报错/警告")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
