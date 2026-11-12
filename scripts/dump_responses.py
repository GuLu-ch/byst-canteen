import json
import os

for k in [k for k in os.environ if "proxy" in k.lower()]:
    os.environ.pop(k, None)

import httpx
from datetime import date, timedelta

BASE = "http://127.0.0.1:8000"
c = httpx.Client(timeout=20, trust_env=False)


def login(phone):
    tok = c.post(f"{BASE}/api/auth/login", json={"phone": phone, "password": "123456"}).json()["token"]
    c.headers["Authorization"] = f"Bearer {tok}"


def show(label, path, **params):
    r = c.get(BASE + path, params=params or None)
    try:
        data = r.json()
    except Exception:
        data = r.text[:200]
    text = json.dumps(data, ensure_ascii=False)
    print(f"--- {label} ({r.status_code}) -> {text[:700]}")


today = date.today()
tomorrow = today + timedelta(days=1)
login("13800000003")
show("availability", "/api/reservations/availability", start=today.isoformat(), end=tomorrow.isoformat())
show("stats/me", "/api/stats/me")
show("reviews/mine", "/api/reviews/mine", day=today.isoformat())
show("votes/options", "/api/votes/options")

login("13800000000")
show("stats/overview", "/api/stats/overview")
show("reservations/summary", "/api/reservations/summary", start=today.isoformat(), end=tomorrow.isoformat())
show("reservations/detail", "/api/reservations/detail", day=tomorrow.isoformat(), meal="lunch")
show("feedback/stats", "/api/feedback/stats", days=7)
show("feedback list", "/api/feedback", page=1, page_size=2)
show("reviews/summary", "/api/reviews/summary", start=(today - timedelta(days=6)).isoformat(), end=today.isoformat())
show("votes/stats", "/api/votes/stats")
show("votes/results", "/api/votes/results")
show("votes/weeks", "/api/votes/weeks")
show("users list", "/api/users", page=1, page_size=2)
show("users/overview", "/api/users/overview")
show("stats/trend", "/api/stats/trend", days=3)
show("settings", "/api/settings")
