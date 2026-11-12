"""后端接口冒烟测试：覆盖登录、菜单、预约、反馈、评价、投票、统计、导出。

用法（后端已在 127.0.0.1:8000 运行）：
    python scripts/smoke_test.py
"""

from __future__ import annotations

import os
import sys
from datetime import date, timedelta

import httpx

# 本机代理常处于关闭状态，且 NO_PROXY 里的 [::1] 会让 httpx 解析失败；这里统一绕过环境代理
for _key in [k for k in os.environ if "proxy" in k.lower()]:
    os.environ.pop(_key, None)

BASE = os.getenv("BYST_BASE", "http://127.0.0.1:8000")
failures: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  ok   {label}")
    else:
        print(f"  FAIL {label} {detail}")
        failures.append(label)


def login(client: httpx.Client, account: str, password: str = "123456", scope: str = "app") -> dict:
    """员工端传手机号；管理端传管理端账号（v8 起是账号+密码，cookie 会话）。"""
    path = "/api/auth/admin-login" if scope == "admin" else "/api/auth/login"
    payload = {"account": account, "password": password} if scope == "admin" else {"phone": account, "password": password}
    resp = client.post(f"{BASE}{path}", json=payload)
    assert resp.status_code == 200, resp.text
    if scope == "admin":
        # cookie 已由 client 保存；同时用 Authorization 头方便断言
        token = resp.cookies.get("byst_admin")
        if token:
            client.headers["Authorization"] = f"Bearer {token}"
    else:
        client.headers["Authorization"] = f"Bearer {resp.json()['token']}"
    return resp.json()["user"]


def main() -> int:
    with httpx.Client(timeout=20) as client:
        print("[健康检查]")
        check("GET /api/health", client.get(f"{BASE}/api/health").json().get("status") == "ok")

        print("[员工端]")
        employee = login(client, "13800000003")
        check("登录成功", employee["role"] == "employee")
        check("错误密码被拒", client.post(f"{BASE}/api/auth/login", json={"phone": "13800000003", "password": "bad"}).status_code == 400)

        public = client.get(f"{BASE}/api/settings/public").json()
        check("公共设置", "deadline" in public and "meal_times" in public)

        today = date.today()
        week = client.get(f"{BASE}/api/menus/week").json()
        check("本周菜单 7 天", len(week["days"]) == 7)

        tomorrow = today + timedelta(days=1)
        availability = client.get(
            f"{BASE}/api/reservations/availability", params={"start": today.isoformat(), "end": (today + timedelta(days=6)).isoformat()}
        ).json()
        check("可预约信息 7 天", len(availability["days"]) == 7)
        open_meals = [
            (day["date"], meal)
            for day in availability["days"]
            for meal, info in day["meals"].items()
            if info["open"]
        ]
        check("存在可预约餐次", len(open_meals) > 0, str(len(open_meals)))
        if open_meals:
            payload = {"items": [{"date": d, "meal": m} for d, m in open_meals[:3]]}
            # 冒烟测试要能反复跑：先把这几餐已有的预约取消掉，才能断言「真的新增成功」。
            existing = {
                (item["date"], item["meal"]): item["id"]
                for item in client.get(f"{BASE}/api/reservations/mine").json()["items"]
                if item["status"] == "reserved"
            }
            for d, m in open_meals[:3]:
                reservation_id = existing.get((d, m))
                if reservation_id:
                    client.delete(f"{BASE}/api/reservations/{reservation_id}")
            bulk = client.post(f"{BASE}/api/reservations/bulk", json=payload)
            check(
                "批量预约",
                bulk.status_code == 200 and bulk.json()["saved"] == len(payload["items"]),
                bulk.text[:200],
            )
        mine = client.get(f"{BASE}/api/reservations/mine").json()
        check("我的预约", isinstance(mine["items"], list))
        me_stats = client.get(f"{BASE}/api/stats/me").json()
        check("我的数据统计", "upcoming_count" in me_stats)

        fb = client.post(f"{BASE}/api/feedback", json={"category": "taste", "content": "冒烟测试：汤有点咸"})
        check("提交反馈", fb.status_code == 200, fb.text[:200])
        check("我的反馈", len(client.get(f"{BASE}/api/feedback/mine").json()) >= 1)

        rv = client.post(f"{BASE}/api/reviews", json={"date": (today - timedelta(days=1)).isoformat(), "meal": "lunch", "rating": 2, "taste": "太咸", "comment": "冒烟测试"})
        check("提交评价（低分带原因）", rv.status_code == 200, rv.text[:200])
        rv2 = client.post(f"{BASE}/api/reviews", json={"date": (today - timedelta(days=1)).isoformat(), "meal": "dinner", "rating": 5, "comment": "冒烟测试晚餐"})
        check("同日另一餐独立评价", rv2.status_code == 200, rv2.text[:200])
        rv_bad = client.post(f"{BASE}/api/reviews", json={"date": (today - timedelta(days=1)).isoformat(), "meal": "supper", "rating": 5})
        check("非法餐次被拒", rv_bad.status_code == 400, rv_bad.text[:200])
        mine_day = client.get(f"{BASE}/api/reviews/mine", params={"day": (today - timedelta(days=1)).isoformat()}).json()
        check("我的评价（按餐次）", isinstance(mine_day, dict) and mine_day.get("lunch") and mine_day.get("dinner"), str(mine_day)[:200])

        opts = client.get(f"{BASE}/api/votes/options").json()
        check("投票选项", "dishes" in opts and "my_votes" in opts)
        if opts.get("open") and opts["dishes"]:
            picks = [dish["name"] for dish in opts["dishes"][:2]]
            vote = client.post(
                f"{BASE}/api/votes",
                json={"week_start": opts["week_start"], "dish_names": picks},
            )
            check("提交投票（多选）", vote.status_code == 200, vote.text[:200])
            check("多选投票已记录", len(vote.json().get("my_votes", [])) == len(picks), vote.text[:200])
            bad = client.post(
                f"{BASE}/api/votes",
                json={"week_start": opts["week_start"], "dish_names": ["不存在的菜"]},
            )
            check("投票菜品校验", bad.status_code == 400, bad.text[:200])
        results = client.get(f"{BASE}/api/votes/results").json()
        check("投票结果", "ranking" in results and "my_votes" in results)

        # v7 登录分离后：员工 token 的 scope=app，访问管理端接口直接 401（scope 不匹配）
        check("员工无后台权限", client.get(f"{BASE}/api/users").status_code in (401, 403))

        print("[登录分离（v8：账号 + httpOnly cookie）]")
        # 员工端 /login 拒绝管理员；管理端 /admin-login 拒绝员工；两种凭证互不通用
        check(
            "员工端拒绝管理员登录",
            client.post(f"{BASE}/api/auth/login", json={"phone": "13800000000", "password": "123456"}).status_code == 403,
        )
        check(
            "管理端拒绝员工登录",
            client.post(f"{BASE}/api/auth/admin-login", json={"account": "13800000003", "password": "123456"}).status_code == 403,
        )
        check(
            "管理端账号错误被拒",
            client.post(f"{BASE}/api/auth/admin-login", json={"account": "nobody", "password": "123456"}).status_code == 400,
        )
        emp_token = client.post(f"{BASE}/api/auth/login", json={"phone": "13800000003", "password": "123456"}).json()["token"]
        r = client.get(f"{BASE}/api/stats/overview", headers={"Authorization": f"Bearer {emp_token}"})
        check("员工 token 不能访问管理端接口", r.status_code == 401, r.text[:120])

        print("[厨师端]")
        login(client, "chef", scope="admin")
        admin_token = client.headers["Authorization"].removeprefix("Bearer ")
        r = client.get(f"{BASE}/api/reservations/mine", headers={"Authorization": f"Bearer {admin_token}"})
        check("管理端 token 不能访问员工端接口", r.status_code == 401, r.text[:120])
        check("管理端身份接口", client.get(f"{BASE}/api/auth/admin-me").json()["role"] == "cook")
        overview = client.get(f"{BASE}/api/stats/overview").json()
        check("后台总览", "today" in overview and "menus" in overview)
        summary = client.get(f"{BASE}/api/reservations/summary", params={"start": today.isoformat(), "end": (today + timedelta(days=3)).isoformat()}).json()
        check("预约汇总", len(summary["days"]) == 4)
        tomorrow_menu = client.get(f"{BASE}/api/menus/day/{tomorrow.isoformat()}").json()
        check("次日菜单", set(tomorrow_menu["meals"]) == {"breakfast", "lunch", "dinner"})
        save = client.put(
            f"{BASE}/api/menus/{tomorrow.isoformat()}/lunch",
            json={"dishes": [{"name": "冒烟红烧肉", "type": "荤菜"}, {"name": "清炒时蔬", "type": "素菜"}], "note": "冒烟测试"},
        )
        check("修改菜单", save.status_code == 200 and len(save.json()["dishes"]) == 2, save.text[:200])
        check("菜单反馈列表", client.get(f"{BASE}/api/feedback").status_code == 200)
        check("评价汇总", client.get(f"{BASE}/api/reviews/summary").json()["total"] >= 1)
        check("投票统计", "ranking" in client.get(f"{BASE}/api/votes/stats").json())
        detail = client.get(f"{BASE}/api/reservations/detail", params={"day": tomorrow.isoformat(), "meal": "lunch"}).json()
        check("预约明细", "items" in detail)
        export = client.get(f"{BASE}/api/reservations/export", params={"start": today.isoformat(), "end": (today + timedelta(days=3)).isoformat()})
        check("导出 Excel", export.status_code == 200 and export.content[:2] == b"PK", str(export.status_code))
        check("厨师无员工管理权限", client.get(f"{BASE}/api/users").status_code == 403)

        print("[管理员端]")
        login(client, "admin", scope="admin")
        users = client.get(f"{BASE}/api/users", params={"page": 1, "page_size": 5}).json()
        check("员工列表", users["total"] >= 10, str(users["total"]))
        created = client.post(f"{BASE}/api/users", json={"phone": "13900000999", "name": "冒烟测试员", "role": "employee", "department": "测试部"})
        if created.status_code != 200:
            # 上一轮跑完留下的测试账号（电话唯一），这次改成编辑它，保证脚本可重复执行。
            same = client.get(f"{BASE}/api/users", params={"q": "13900000999"}).json()["items"]
            if same:
                created = client.put(
                    f"{BASE}/api/users/{same[0]['id']}",
                    json={"name": "冒烟测试员", "department": "测试部", "is_active": True},
                )
        check("新增员工", created.status_code == 200, created.text[:200])
        if created.status_code == 200:
            uid = created.json()["id"]
            check("停用员工", client.delete(f"{BASE}/api/users/{uid}").status_code == 200)
        check("员工导入模板", client.get(f"{BASE}/api/users/template").content[:2] == b"PK")
        settings = client.get(f"{BASE}/api/settings").json()
        check("读取设置", "deadline" in settings)
        settings["deadline"]["lunch"] = "19:30"
        updated = client.put(f"{BASE}/api/settings", json={"values": settings})
        check("保存设置", updated.status_code == 200 and updated.json()["deadline"]["lunch"] == "19:30", updated.text[:200])
        check("设置校验", client.put(f"{BASE}/api/settings", json={"values": {"deadline": {"lunch": "25:00"}}}).status_code == 400)
        check("预约趋势", len(client.get(f"{BASE}/api/stats/trend", params={"days": 7}).json()["series"]) == 7)

    print()
    if failures:
        print(f"失败 {len(failures)} 项：" + "、".join(failures))
        return 1
    print("全部通过 ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
