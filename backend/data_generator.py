"""
Модуль генерації синтетичних логістичних сценаріїв.
"""

import random
import math


VEHICLE_TYPES = [
    {"type": "Піший",  "max_weight": 5.0,  "max_dist": 3.0,  "min_price": 50},
    {"type": "Велосипед", "max_weight": 15.0, "max_dist": 10.0, "min_price": 80},
    {"type": "Мотоцикл", "max_weight": 30.0, "max_dist": 25.0, "min_price": 100},
    {"type": "Авто",   "max_weight": 200.0, "max_dist": 60.0, "min_price": 150},
    {"type": "Мікровантажівка", "max_weight": 1000.0, "max_dist": 100.0, "min_price": 300},
]

HUB_NAMES = [
    "Маркет «Центральний»",
    "Маркет «Лівобережний»",
    "Маркет «Оболонь»",
    "Маркет «Позняки»",
    "Маркет «Борщагівка»",
    "Маркет «Троєщина»",
    "Маркет «Відрадний»",
    "Маркет «Сирець»",
    "Маркет «Теремки»",
    "Маркет «Дарниця»",
    "Маркет «Голосіївський»",
    "Маркет «Печерський»",
    "Маркет «Шевченківський»",
    "Маркет «Подільський»",
    "Маркет «Святошинський»",
    "Маркет «Дніпровський»",
    "Маркет «Солом'янський»",
    "Маркет «Оболонський»",
    "Маркет «Північний»",
    "Маркет «Південний»",
    "Маркет «Східний»",
    "Маркет «Західний»",
    "Маркет «Нове місто»",
    "Маркет «Старе місто»",
    "Маркет «Парковий»",
    "Маркет «Лісовий»",
    "Маркет «Березовий»",
    "Маркет «Озерний»",
    "Маркет «Спортивний»",
    "Маркет «Київський»",
    "Маркет «Каштановий»",
    "Маркет «Вишневий»",
    "Маркет «Фестивальний»",
    "Маркет «Набережний»",
    "Маркет «Університетський»",
    "Маркет «Промисловий»",
    "Маркет «Міський»",
    "Маркет «Транспортний»",
    "Маркет «Молодіжний»",
    "Маркет «Святковий»",
    "Маркет «Піщаний»",
    "Маркет «Степовий»",
    "Маркет «Хвойний»",
    "Маркет «Жовтневий»",
    "Маркет «Журавлиний»",
    "Маркет «Річковий»",
    "Маркет «Промінний»",
    "Маркет «Зоряний»",
    "Маркет «Мрійливий»",
    "Маркет «Кам'яний»",
    "Маркет «Квітковий»",
]

COURIER_NAMES = [
    "Іван Петренко", "Олена Коваль", "Микола Сидоренко", "Тетяна Бондар",
    "Андрій Мельник", "Наталя Кравченко", "Сергій Шевченко", "Ірина Лисенко",
    "Василь Тимченко", "Людмила Гриценко", "Павло Дяченко", "Оксана Руденко",
    "Дмитро Пономаренко", "Галина Захаренко", "Олег Марченко",
]


def _rand_point(lat_range, lon_range):
    return (
        random.uniform(lat_range[0], lat_range[1]),
        random.uniform(lon_range[0], lon_range[1]),
    )


def _distance(lat1, lon1, lat2, lon2):
    """Приблизна відстань у градусах (для простоти)."""
    return math.sqrt((lat1 - lat2)**2 + (lon1 - lon2)**2)


def generate_scenario(n_orders, n_hubs, n_couriers, lat_range, lon_range, noise_pct=0.05):
    """
    Генерує повний симуляційний сценарій:
      - n_hubs хабів
      - n_orders замовлень (cluster-distributed + noise outliers)
      - n_couriers кур'єрів з різними типами ТЗ
    """
    random.seed(None)

    hubs = []
    min_hub_distance = 0.05  # ~5 км
    attempts = 0
    max_attempts = 1000
    while len(hubs) < n_hubs and attempts < max_attempts:
        lat, lon = _rand_point(lat_range, lon_range)
        if lat < lat_range[0] + 0.02:
            continue
        too_close = any(_distance(lat, lon, h["lat"], h["lon"]) < min_hub_distance for h in hubs)
        if not too_close:
            hubs.append({
                "hub_id": len(hubs) + 1,
                "name":   HUB_NAMES[len(hubs)] if len(hubs) < len(HUB_NAMES) else f"Маркет «Зона {len(hubs)+1}»",
                "lat":    round(lat, 6),
                "lon":    round(lon, 6),
            })
        attempts += 1
    if len(hubs) < n_hubs:
        for i in range(n_hubs - len(hubs)):
            lat, lon = _rand_point(lat_range, lon_range)
            hubs.append({
                "hub_id": len(hubs) + 1,
                "name":   HUB_NAMES[len(hubs)] if len(hubs) < len(HUB_NAMES) else f"Маркет «Зона {len(hubs)+1}»",
                "lat":    round(lat, 6),
                "lon":    round(lon, 6),
            })

    n_noise   = max(1, int(n_orders * noise_pct))
    n_cluster = n_orders - n_noise
    orders    = []
    oid       = 1

    per_hub = n_cluster // n_hubs
    remainder = n_cluster % n_hubs
    for i, hub in enumerate(hubs):
        count = per_hub + (1 if i < remainder else 0)
        for _ in range(count):
            spread = 0.08  # збільшено для більшої розсіяності
            lat = hub["lat"] + random.gauss(0, spread)
            lon = hub["lon"] + random.gauss(0, spread)
            lat = max(lat_range[0] - 0.1, min(lat_range[1] + 0.1, lat))
            lon = max(lon_range[0] - 0.1, min(lon_range[1] + 0.1, lon))
            if lat < lat_range[0] + 0.02:
                lat += 0.05  # змістити на північ
            orders.append({
                "order_id":   oid,
                "lat":        round(lat, 6),
                "lon":        round(lon, 6),
                "weight":     round(random.uniform(0.5, 50.0), 2),
                "price":      round(random.uniform(30.0, 500.0), 2),
                "status":     "Вільне",
                "hub_id":     None,
                "courier_id": None,
            })
            oid += 1

    noise_lat_range = [lat_range[0] - 0.3, lat_range[0] - 0.1]
    noise_lon_range = [lon_range[1] + 0.1, lon_range[1] + 0.3]
    for _ in range(n_noise):
        lat, lon = _rand_point(noise_lat_range, noise_lon_range)
        orders.append({
            "order_id":   oid,
            "lat":        round(lat, 6),
            "lon":        round(lon, 6),
            "weight":     round(random.uniform(0.5, 50.0), 2),
            "price":      round(random.uniform(30.0, 500.0), 2),
            "status":     "Вільне",
            "hub_id":     None,
            "courier_id": None,
        })
        oid += 1

    random.shuffle(orders)

    couriers = []
    names_pool = COURIER_NAMES.copy()
    random.shuffle(names_pool)
    for i in range(n_couriers):
        vt = random.choice(VEHICLE_TYPES)
        hub = hubs[i % len(hubs)]
        couriers.append({
            "courier_id":   i + 1,
            "name":         names_pool[i % len(names_pool)],
            "vehicle_type": vt["type"],
            "hub_id":       hub["hub_id"],
            "max_weight":   vt["max_weight"],
            "max_dist_km":  vt["max_dist"],
            "min_price":    vt["min_price"],
        })

    return {"hubs": hubs, "orders": orders, "couriers": couriers}
