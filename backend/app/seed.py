from __future__ import annotations

import random
from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session

from .models import DishTag, Feedback, Menu, Reservation, Review, Setting, User, Vote
from .utils import hash_password, json_dumps, week_start_of

DEFAULT_PASSWORD = "123456"

# 菜品类型标签（独立表，添加菜品时可回车扩充）
DISH_TAGS = ["主食", "荤菜", "素菜", "汤品", "小菜", "凉菜", "其他", "甜点"]

EMPLOYEES = [
    ("13800000003", "陈晨", "技术部"),
    ("13800000004", "林小雨", "产品部"),
    ("13800000005", "赵磊", "技术部"),
    ("13800000006", "孙悦", "市场部"),
    ("13800000007", "周文", "财务部"),
    ("13800000008", "吴倩", "人事部"),
    ("13800000009", "郑浩", "技术部"),
    ("13800000010", "冯雪", "运营部"),
    ("13800000011", "何俊", "产品部"),
    ("13800000012", "许静", "市场部"),
    ("13800000013", "曹阳", "技术部"),
    ("13800000014", "沈佳", "运营部"),
]

BREAKFAST_MAIN = [
    "小米南瓜粥",
    "皮蛋瘦肉粥",
    "现磨豆浆",
    "豆腐脑",
    "鲜肉包",
    "香菇菜包",
    "葱油饼",
    "鸡蛋灌饼",
    "阳春面",
    "小馄饨",
    "蒸玉米",
    "蒸红薯",
]
BREAKFAST_SIDE = ["凉拌黄瓜", "酸豆角", "榨菜丝", "凉拌木耳", "海带丝", "腐乳", "水煮蛋", "煎蛋"]

MEAT = [
    "红烧肉",
    "糖醋排骨",
    "宫保鸡丁",
    "鱼香肉丝",
    "黑椒牛柳",
    "香菇滑鸡",
    "红烧鱼块",
    "回锅肉",
    "可乐鸡翅",
    "青椒肉丝",
    "香辣虾",
    "土豆烧牛腩",
]
VEG = [
    "麻婆豆腐",
    "番茄炒蛋",
    "蒜蓉西兰花",
    "清炒时蔬",
    "干煸四季豆",
    "地三鲜",
    "酸辣土豆丝",
    "上汤娃娃菜",
    "红烧茄子",
    "手撕包菜",
    "蚝油生菜",
    "木耳山药",
]
SOUP = ["紫菜蛋花汤", "冬瓜排骨汤", "玉米排骨汤", "罗宋汤", "番茄蛋汤", "菌菇鸡汤", "海带豆腐汤", "绿豆汤"]
STAPLE = ["米饭", "杂粮饭", "馒头"]

FEEDBACK_SAMPLES = [
    ("taste", "今天的番茄炒蛋有点偏咸，希望下次少放一点盐。", True),
    ("oil", "中午的干煸四季豆油有点大，吃完有些腻。", False),
    ("fresh", "周三的青菜看着不太新鲜，叶子有点发黄。", True),
    ("hygiene", "餐盘回收处的地面有点滑，建议增加防滑垫并及时清理。", False),
    ("tableware", "汤勺有几个没洗干净，麻烦检查一下消毒环节。", True),
    ("other", "希望早餐能增加无糖豆浆，照顾一下控糖的同事。", False),
    ("taste", "最近的菜整体偏辣，能不能标注一下辣度？", False),
    ("oil", "红烧肉很好吃，但连续两周出现两次了，可以换换花样。", True),
    ("fresh", "水果捞的西瓜很甜，点赞！", True),
    ("hygiene", "打饭窗口的口罩佩戴可以再规范一些。", False),
    ("tableware", "建议增加一些小的调味碟，方便分装辣酱。", False),
    ("other", "周五的加餐很棒，希望每周都有一次特色菜。", True),
]

REVIEW_COMMENTS = {
    5: ["红烧肉入口即化，今天的米饭也很香！", "菜量足，味道刚刚好，吃得很满足。", "汤很好喝，温度也合适。"],
    4: ["整体不错，就是排队稍微久了一点。", "味道挺好的，素菜可以再多一点。", "比上周有进步，继续保持。"],
    3: ["中规中矩，荤菜稍微少了一些。", "今天的菜有点凉了，其他都还好。"],
    2: ["菜太咸了，吃完一直在喝水。", "荤菜太少，几乎都是素的。"],
    1: ["米饭夹生，菜也没什么味道。", "食材不太新鲜，希望重视一下。"],
}
TASTE_REASONS = ["太咸", "太淡", "太辣", "不够辣", "太软", "太硬", "不熟", "其他"]
PAIRING_REASONS = ["荤菜太少", "素菜太少", "种类重复", "搭配不合理"]
PORTION_REASONS = ["太少", "太多", "刚好"]


def _pick(pool: list[str], count: int, offset: int) -> list[str]:
    start = offset % len(pool)
    rotated = pool[start:] + pool[:start]
    return rotated[:count]


def build_menu(d: date, meal: str) -> list[dict]:
    offset = d.toordinal() + (0 if meal == "breakfast" else 3 if meal == "lunch" else 6)
    if meal == "breakfast":
        dishes = [{"name": name, "type": "主食"} for name in _pick(BREAKFAST_MAIN, 2, offset)]
        dishes += [{"name": name, "type": "小菜"} for name in _pick(BREAKFAST_SIDE, 2, offset + 2)]
        return dishes
    if meal == "lunch":
        dishes = [{"name": name, "type": "荤菜"} for name in _pick(MEAT, 2, offset)]
        dishes += [{"name": name, "type": "素菜"} for name in _pick(VEG, 2, offset + 1)]
        dishes += [{"name": _pick(SOUP, 1, offset + 2)[0], "type": "汤品"}]
        dishes += [{"name": _pick(STAPLE, 1, offset)[0], "type": "主食"}]
        return dishes
    dishes = [{"name": name, "type": "荤菜"} for name in _pick(MEAT, 1, offset + 4)]
    dishes += [{"name": name, "type": "素菜"} for name in _pick(VEG, 2, offset + 5)]
    dishes += [{"name": _pick(SOUP, 1, offset + 6)[0], "type": "汤品"}]
    dishes += [{"name": _pick(STAPLE, 1, offset + 1)[0], "type": "主食"}]
    return dishes


def seed(db: Session) -> bool:
    if db.query(User).count() > 0:
        return False

    rng = random.Random(20261111)
    now = datetime.now()
    today = now.date()

    users = [
        User(
            phone="13800000000",
            username="admin",
            name="张伟",
            role="admin",
            department="行政部",
            password_hash=hash_password(DEFAULT_PASSWORD),
            taste="清淡",
        ),
        User(
            phone="13800000001",
            username="chef",
            name="李建国",
            role="cook",
            department="食堂",
            password_hash=hash_password(DEFAULT_PASSWORD),
            taste="家常",
            favorite_dishes="红烧肉、糖醋排骨",
        ),
        User(
            phone="13800000002",
            username="chef2",
            name="王秀兰",
            role="cook",
            department="食堂",
            password_hash=hash_password(DEFAULT_PASSWORD),
            taste="少油少盐",
        ),
    ]
    profiles = {
        "13800000003": ("不吃香菜", "偏辣", "水煮鱼、麻辣香锅"),
        "13800000004": ("海鲜过敏", "清淡", "番茄炒蛋、上汤娃娃菜"),
        "13800000005": ("", "重口", "回锅肉、麻婆豆腐"),
        "13800000006": ("不吃内脏", "少油", "蒜蓉西兰花、清蒸鱼"),
        "13800000007": ("乳糖不耐", "清淡", "小米粥、蒸红薯"),
        "13800000008": ("", "微辣", "宫保鸡丁、酸辣土豆丝"),
        "13800000009": ("花生过敏", "偏甜", "糖醋排骨、可乐鸡翅"),
        "13800000010": ("不吃牛肉", "清淡", "香菇滑鸡、蚝油生菜"),
        "13800000011": ("", "重辣", "香辣虾、干煸四季豆"),
        "13800000012": ("不吃葱", "少盐", "清炒时蔬、冬瓜排骨汤"),
        "13800000013": ("", "正常", "红烧肉、鱼香肉丝"),
        "13800000014": ("海鲜过敏", "清淡", "番茄蛋汤、手撕包菜"),
    }
    for phone, name, dept in EMPLOYEES:
        allergens, taste, favorites = profiles.get(phone, ("", "", ""))
        users.append(
            User(
                phone=phone,
                name=name,
                role="employee",
                department=dept,
                password_hash=hash_password(DEFAULT_PASSWORD),
                allergens=allergens,
                taste=taste,
                favorite_dishes=favorites,
                preferences="希望多一些时令蔬菜" if phone.endswith("4") else "",
            )
        )
    db.add_all(users)
    db.commit()

    # 菜品类型标签
    db.add_all([DishTag(name=name) for name in DISH_TAGS])
    db.commit()

    # 菜单：过去四周的周一到未来下下周的周五（周末不供餐），
    # 覆盖「本周 / 最近30天」全部区间，历史日期也能看到当时吃的是什么。
    this_monday = week_start_of(today)
    menu_start = this_monday - timedelta(days=28)
    menu_end = this_monday + timedelta(days=20)
    menus: dict[tuple[date, str], Menu] = {}
    for i in range((menu_end - menu_start).days + 1):
        d = menu_start + timedelta(days=i)
        if d.weekday() >= 5:  # 周六日没有菜单
            continue
        for meal in ("breakfast", "lunch", "dinner"):
            menu = Menu(
                date=d,
                meal=meal,
                dishes=json_dumps(build_menu(d, meal)),
                note="米饭、杂粮饭、馒头自助" if meal != "breakfast" else "早餐 07:30 开始供应",
            )
            db.add(menu)
            menus[(d, meal)] = menu
    db.commit()

    employees = [u for u in users if u.role == "employee"]

    # 预约：过去 14 天 + 今天起 10 天（周末不供餐，只约工作日），
    # 这样「最近30天 / 本周 / 今日」三个区间都有真实数据可看。
    for offset in range(-14, 11):
        d = today + timedelta(days=offset)
        if d.weekday() >= 5:
            continue
        # 越早的日期预约率略低，模拟食堂逐步推广的过程
        decay = 0.75 if offset < -7 else 1.0
        for user in employees:
            for meal, probability in (("breakfast", 0.45), ("lunch", 0.88), ("dinner", 0.4)):
                if rng.random() < probability * decay:
                    db.add(Reservation(user_id=user.id, date=d, meal=meal, status="reserved"))
    db.commit()

    # 意见反馈：26 条（近 30 天分布，约一半已处理），让分页效果明显
    FEEDBACK_STATUSES = [True, True, False, True, True, False, True, True, False, True, False, True]
    for idx, (category, content, _) in enumerate(FEEDBACK_SAMPLES):
        handled = FEEDBACK_STATUSES[idx % len(FEEDBACK_STATUSES)]
        d = today - timedelta(days=rng.randint(0, 20))
        db.add(
            Feedback(
                user_id=rng.choice(employees).id,
                category=category,
                content=content,
                date=d,
                handled=handled,
                created_at=datetime.combine(d, time(rng.randint(8, 18), rng.randint(0, 59))),
            )
        )
    # 补足到 26 条：内容复用样例，日期散开
    extra = 26 - len(FEEDBACK_SAMPLES)
    for idx in range(extra):
        category, content, _ = FEEDBACK_SAMPLES[(idx * 5 + 3) % len(FEEDBACK_SAMPLES)]
        d = today - timedelta(days=rng.randint(1, 25))
        db.add(
            Feedback(
                user_id=rng.choice(employees).id,
                category=category,
                content=content,
                date=d,
                handled=rng.random() < 0.55,
                created_at=datetime.combine(d, time(rng.randint(8, 18), rng.randint(0, 59))),
            )
        )
    db.commit()

    # 评价：过去 30 天，每天三餐都有不少人打分（最近几天更活跃），支持每天平均分趋势
    ratings = [5, 5, 5, 4, 4, 4, 4, 3, 3, 2, 2, 1]
    meal_hours = {"breakfast": (8, 9), "lunch": (12, 13), "dinner": (18, 19)}
    for offset in range(30):
        d = today - timedelta(days=offset)
        if d.weekday() >= 5:
            continue
        active = 0.9 if offset < 7 else 0.55
        for user in employees:
            chosen = [
                m
                for m in ("lunch", "dinner", "breakfast")
                if rng.random() < (0.5 if m != "breakfast" else 0.2) * active
            ]
            if not chosen:
                chosen = [rng.choice(["lunch", "dinner"])]
            for meal in chosen:
                rating = rng.choice(ratings)
                taste = pairing = portion = ""
                comment = ""
                if rating <= 2:
                    taste = rng.choice(TASTE_REASONS) if rng.random() < 0.7 else ""
                    pairing = rng.choice(PAIRING_REASONS) if rng.random() < 0.5 else ""
                    portion = rng.choice(PORTION_REASONS) if rng.random() < 0.5 else ""
                    comment = rng.choice(REVIEW_COMMENTS[rating])
                elif rating == 3 and rng.random() < 0.4:
                    comment = rng.choice(REVIEW_COMMENTS[3])
                h_lo, h_hi = meal_hours[meal]
                db.add(
                    Review(
                        user_id=user.id,
                        date=d,
                        meal=meal,
                        rating=rating,
                        taste=taste,
                        pairing=pairing,
                        portion=portion,
                        comment=comment,
                        created_at=datetime.combine(d, time(rng.randint(h_lo, h_hi), rng.randint(0, 59))),
                    )
                )
    db.commit()

    # 本周 + 上周的菜品投票（让「最近30天 / 本周」都有投票数据）
    this_monday = week_start_of(today)
    dish_names = []
    for meal in ("lunch", "dinner"):
        for i in range(7):
            d = this_monday + timedelta(days=i)
            menu = menus.get((d, meal))
            if menu:
                import json

                for dish in json.loads(menu.dishes):
                    if dish["type"] in ("荤菜", "素菜") and dish["name"] not in dish_names:
                        dish_names.append(dish["name"])
    for week_offset in (0, -7):
        target_week = this_monday + timedelta(days=week_offset)
        voters = rng.sample(employees, k=10)
        for user in voters:
            # 多选投票：每人投 1~3 道菜
            picks = rng.sample(dish_names, k=min(len(dish_names), rng.randint(1, 3)))
            for name in picks:
                db.add(Vote(user_id=user.id, week_start=target_week, dish_name=name))
    db.commit()

    # 默认设置落库，方便后台直接编辑
    defaults = {
        "deadline": {"breakfast": "20:00", "lunch": "20:00", "dinner": "20:00"},
        "open_days": 7,
        "announcement": "本周五午餐加餐：红烧排骨、蒜蓉西兰花，欢迎品尝～",
    }
    for key, value in defaults.items():
        if db.get(Setting, key) is None:
            db.add(Setting(key=key, value=json_dumps(value)))
    db.commit()
    return True


def ensure_staff_accounts(db) -> list[str]:
    """给历史库里的管理员/厨师补上登录账号（v8 起管理端用账号+密码登录）。

    已存在账号的保持不变；没有的按 admin / chef 顺延分配，返回新分配的账号。
    """
    staff = db.query(User).filter(User.role.in_(("admin", "cook"))).order_by(User.id.asc()).all()
    used = {(user.username or "").lower() for user in staff if user.username}
    assigned: list[str] = []
    for user in staff:
        if user.username:
            continue
        base = "admin" if user.role == "admin" else "chef"
        candidate = base
        index = 2
        while candidate.lower() in used:
            candidate = f"{base}{index}"
            index += 1
        user.username = candidate
        used.add(candidate.lower())
        assigned.append(candidate)
    if assigned:
        db.commit()
    return assigned
