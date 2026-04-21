"""
Модуль просторової кластеризації:
  - K-Means (прив'язка до фіксованих хабів)
  - DBSCAN (виявлення аномалій)
  - OPTICS (змінна щільність)
"""

import math
import time
from collections import defaultdict


def _haversine(lat1, lon1, lat2, lon2):
    """Відстань у км між двома геоточками (формула Гаверсина)."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi  = math.radians(lat2 - lat1)
    dlam  = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return 2 * R * math.asin(math.sqrt(a))


# ─────────────────────────────────────────────
# K-Means (з фіксованими центроїдами = хаби)
# ─────────────────────────────────────────────

def run_kmeans(orders, hubs):
    """
    Реалізація K-Means з фіксованими центроїдами (координатами хабів).
    Кожне замовлення просто прив'язується до найближчого хабу (формування зон Вороного).
    Повертає assignments {order_id: hub_id} та WCSS.
    """
    t0 = time.time()

    if not hubs or not orders:
        return {"assignments": {}, "wcss": 0, "exec_ms": 0}

    # Фіксовані координати хабів
    centroids = {h["hub_id"]: [h["lat"], h["lon"]] for h in hubs}
    hub_ids   = [h["hub_id"] for h in hubs]
    assignments = {}

    # Прив'язка кожного замовлення до найближчого хабу
    for o in orders:
        best_hub  = None
        best_dist = float('inf')
        for hid in hub_ids:
            c = centroids[hid]
            d = _haversine(o["lat"], o["lon"], c[0], c[1])
            if d < best_dist:
                best_dist = d
                best_hub  = hid
        assignments[o["order_id"]] = best_hub

    # Підрахунок WCSS (сума квадратів відстаней)
    wcss = 0.0
    for o in orders:
        hid = assignments.get(o["order_id"])
        if hid:
            c = centroids[hid]
            d = _haversine(o["lat"], o["lon"], c[0], c[1])
            wcss += d * d

    exec_ms = round((time.time() - t0) * 1000, 1)
    return {"assignments": assignments, "wcss": round(wcss, 2), "exec_ms": exec_ms}


# ─────────────────────────────────────────────
# DBSCAN
# ─────────────────────────────────────────────

def run_dbscan(orders, hubs, eps_km, min_pts):
    """
    DBSCAN з геодезичними відстанями.
    Після кластеризації кожна валідна точка (не шум) прив'язується до найближчого хабу.
    eps_km — радіус околиці у кілометрах.
    """
    t0 = time.time()
    n  = len(orders)
    if n == 0:
        return {"assignments": {}, "wcss": None, "exec_ms": 0}

    labels   = [-2] * n   # -2 = unvisited
    cluster_id = 0

    def range_query(idx):
        return [j for j in range(n) if j != idx and
                _haversine(orders[idx]["lat"], orders[idx]["lon"],
                        orders[j]["lat"],  orders[j]["lon"]) <= eps_km]

    for i in range(n):
        if labels[i] != -2:
            continue
        neighbors = range_query(i)
        if len(neighbors) < min_pts:
            labels[i] = -1  # noise
            continue
        labels[i] = cluster_id
        seed_set  = set(neighbors)
        while seed_set:
            q = seed_set.pop()
            if labels[q] == -1:
                labels[q] = cluster_id
            if labels[q] != -2:
                continue
            labels[q]   = cluster_id
            q_neighbors = range_query(q)
            if len(q_neighbors) >= min_pts:
                seed_set.update(q_neighbors)
        cluster_id += 1

    def nearest_hub(lat, lon):
        return min(hubs, key=lambda h: _haversine(lat, lon, h["lat"], h["lon"]))["hub_id"]

    assignments = {}
    for i, o in enumerate(orders):
        lbl = labels[i]
        if lbl == -1:
            assignments[o["order_id"]] = None   # Аномалія (шум)
        else:
            # Прив'язуємо замовлення до його найближчого хабу
            assignments[o["order_id"]] = nearest_hub(o["lat"], o["lon"])

    exec_ms = round((time.time() - t0) * 1000, 1)
    return {"assignments": assignments, "wcss": None, "exec_ms": exec_ms}


# ─────────────────────────────────────────────
# OPTICS
# ─────────────────────────────────────────────

def run_optics(orders, hubs, min_pts, max_eps=10.0):
    """
    Спрощена реалізація OPTICS.
    Будує впорядкований список досяжності, потім витягує кластери.
    Кожна валідна точка прив'язується до найближчого хабу.
    """
    t0 = time.time()
    n  = len(orders)
    if n == 0:
        return {"assignments": {}, "wcss": None, "exec_ms": 0}

    UNDEFINED = float('inf')

    def core_dist(idx, neighbors):
        if len(neighbors) < min_pts:
            return UNDEFINED
        dists = sorted(_haversine(orders[idx]["lat"], orders[idx]["lon"],
                                orders[j]["lat"],  orders[j]["lon"])
                    for j in neighbors)
        return dists[min_pts - 1]

    def get_neighbors(idx):
        return [j for j in range(n) if j != idx and
                _haversine(orders[idx]["lat"], orders[idx]["lon"],
                        orders[j]["lat"],  orders[j]["lon"]) <= max_eps]

    reach_dist  = [UNDEFINED] * n
    processed   = [False] * n
    ordered_pts = []

    for i in range(n):
        if processed[i]:
            continue
        neighbors   = get_neighbors(i)
        processed[i] = True
        ordered_pts.append(i)
        cd = core_dist(i, neighbors)
        if cd == UNDEFINED:
            continue
        seeds = {}
        for j in neighbors:
            if processed[j]:
                continue
            new_rd = max(cd, _haversine(orders[i]["lat"], orders[i]["lon"],
                                        orders[j]["lat"], orders[j]["lon"]))
            if reach_dist[j] == UNDEFINED or new_rd < reach_dist[j]:
                reach_dist[j] = new_rd
                seeds[j] = new_rd
        while seeds:
            q = min(seeds, key=lambda x: seeds[x])
            del seeds[q]
            if processed[q]:
                continue
            processed[q] = True
            ordered_pts.append(q)
            q_neighbors = get_neighbors(q)
            q_cd = core_dist(q, q_neighbors)
            if q_cd == UNDEFINED:
                continue
            for j in q_neighbors:
                if processed[j]:
                    continue
                new_rd = max(q_cd, _haversine(orders[q]["lat"], orders[q]["lon"],
                                            orders[j]["lat"], orders[j]["lon"]))
                if reach_dist[j] == UNDEFINED or new_rd < reach_dist[j]:
                    reach_dist[j] = new_rd
                    seeds[j] = new_rd

    # Extract clusters: group points where reach_dist <= threshold into clusters
    finite_rd = [r for r in reach_dist if r != UNDEFINED]
    if finite_rd:
        mean_rd = sum(finite_rd) / len(finite_rd)
        threshold = 2 * mean_rd
    else:
        threshold = 0.1

    labels = [-1] * n  # default noise
    cluster_id = 0
    in_cluster = False
    for pt in ordered_pts:
        rd = reach_dist[pt]
        if rd != UNDEFINED and rd <= threshold:
            if not in_cluster:
                cluster_id += 1
                in_cluster = True
            labels[pt] = cluster_id
        else:
            in_cluster = False
            labels[pt] = -1

    def nearest_hub(lat, lon):
        return min(hubs, key=lambda h: _haversine(lat, lon, h["lat"], h["lon"]))["hub_id"]

    assignments = {}
    for i, o in enumerate(orders):
        lbl = labels[i]
        if lbl == -1:
            assignments[o["order_id"]] = None  # Аномалія (шум)
        else:
            # Прив'язуємо замовлення до його найближчого хабу
            assignments[o["order_id"]] = nearest_hub(o["lat"], o["lon"])

    exec_ms = round((time.time() - t0) * 1000, 1)
    return {"assignments": assignments, "wcss": None, "exec_ms": exec_ms}