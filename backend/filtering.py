"""
Модуль багатокритеріальної фільтрації замовлень для кур'єра.
Реалізує Rule-based кон'юнктивний відбір: A* = { a ∈ A | ∀ P_j(x_ij) = true }
Складність: O(n·m), де n — кількість замовлень, m — кількість критеріїв.
"""

import math


def _haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return 2 * R * math.asin(math.sqrt(a))


def filter_orders(orders, max_weight=None, min_price=None,
                max_price=None, min_weight=None,
                max_dist_km=None, hub_coords=None):
    """
    Застосовує систему логічних предикатів до масиву замовлень.

    Предикати (всі кон'юнктивні):
      P1: weight  ≤ max_weight    (максимальна вага вантажу)
      P2: price   ≥ min_price     (мінімальна вартість замовлення)
      P3: price   ≤ max_price     (максимальна вартість)
      P4: weight  ≥ min_weight    (мінімальна вага)
      P5: dist_km ≤ max_dist_km   (максимальна відстань від хабу)

    Повертає відфільтровані замовлення зі збагаченим полем dist_km.
    """
    result = []
    for order in orders:
        # P1: max weight
        if max_weight is not None and order["weight"] > max_weight:
            continue
        # P2: min price
        if min_price is not None and order["price"] < min_price:
            continue
        # P3: max price
        if max_price is not None and order["price"] > max_price:
            continue
        # P4: min weight
        if min_weight is not None and order["weight"] < min_weight:
            continue
        # P5: distance from hub
        dist_km = None
        if hub_coords is not None:
            dist_km = _haversine(hub_coords[0], hub_coords[1],
                                order["lat"], order["lon"])
            if max_dist_km is not None and dist_km > max_dist_km:
                continue
        enriched         = dict(order)
        enriched["dist"] = round(dist_km, 2) if dist_km is not None else None
        result.append(enriched)
    return result
