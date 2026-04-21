"""
Тестувально-навчальний комплекс логістичної діяльності
Бекенд-сервер: Flask REST API
"""

from flask import Flask, jsonify, request, send_from_directory
import json
import os
import sys
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_generator import generate_scenario
from clustering import run_kmeans, run_dbscan, run_optics
from filtering import filter_orders

app = Flask(__name__, static_folder='../frontend', static_url_path='')

@app.after_request
def add_cors(r):
    r.headers['Access-Control-Allow-Origin'] = '*'
    r.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    r.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    return r

# In-memory state
state = {
    "hubs": [],
    "orders": [],
    "couriers": [],
    "clusters": {},   # hub_id -> [order_ids]
    "clustered": False
}


@app.route('/')
def index():
    return send_from_directory('../frontend', 'index.html')


# ─────────────────────────────────────────────
# СЦЕНАРІЙ: генерація / завантаження
# ─────────────────────────────────────────────

@app.route('/api/scenario/generate', methods=['POST'])
def generate():
    """Генерує новий симуляційний сценарій."""
    params = request.get_json(force=True)
    n_orders    = int(params.get('n_orders', 100))
    n_hubs      = int(params.get('n_hubs', 5))
    n_couriers  = int(params.get('n_couriers', 10))
    lat_range   = params.get('lat_range', [50.3, 50.6])
    lon_range   = params.get('lon_range', [30.4, 30.7])
    noise_pct   = float(params.get('noise_pct', 0.05))

    data = generate_scenario(n_orders, n_hubs, n_couriers, lat_range, lon_range, noise_pct)
    state["hubs"]      = data["hubs"]
    state["orders"]    = data["orders"]
    state["couriers"]  = data["couriers"]
    state["clusters"]  = {}
    state["clustered"] = False

    return jsonify({"status": "ok", "summary": {
        "n_orders":   len(state["orders"]),
        "n_hubs":     len(state["hubs"]),
        "n_couriers": len(state["couriers"])
    }})


@app.route('/api/scenario/upload', methods=['POST'])
def upload():
    """Завантажує Excel або CSV з замовленнями."""
    f = request.files.get('file')
    if not f:
        return jsonify({"error": "Файл не надано"}), 400
    try:
        if f.filename.endswith('.csv'):
            import io, csv
            content = f.read().decode('utf-8')
            reader = csv.DictReader(io.StringIO(content))
            orders = []
            for i, row in enumerate(reader):
                if not {'lat', 'lon', 'weight', 'price'}.issubset(row.keys()):
                    return jsonify({"error": f"Відсутні колонки. Потрібні: lat,lon,weight,price"}), 422
                try:
                    orders.append({
                        "order_id": i + 1,
                        "lat":    float(row['lat']),
                        "lon":    float(row['lon']),
                        "weight": float(row['weight']),
                        "price":  float(row['price']),
                        "status": "Вільне",
                        "hub_id": None,
                        "courier_id": None
                    })
                except ValueError as e:
                    return jsonify({"error": f"Рядок {i+2}: {e}"}), 422
        else:
            # Excel
            if f.filename.endswith(('.xlsx', '.xlsm')):
                df = pd.read_excel(f, engine='openpyxl')
            elif f.filename.endswith('.xls'):
                df = pd.read_excel(f, engine='xlrd')
            else:
                return jsonify({"error": "Непідтримуваний формат файлу. Використовуйте .xlsx, .xls або .csv"}), 400
            orders = []
            required = {'lat', 'lon', 'weight', 'price'}
            if not all(col in df.columns for col in required):
                return jsonify({"error": f"Відсутні колонки: {required}"}), 422
            for i, row in df.iterrows():
                try:
                    orders.append({
                        "order_id": i + 1,
                        "lat":    float(row['lat']),
                        "lon":    float(row['lon']),
                        "weight": float(row['weight']),
                        "price":  float(row['price']),
                        "status": "Вільне",
                        "hub_id": None,
                        "courier_id": None
                    })
                except ValueError as e:
                    return jsonify({"error": f"Рядок {i+2}: {e}"}), 422
    except Exception as e:
        return jsonify({"error": f"Помилка читання файлу: {str(e)}"}), 400

    state["orders"]    = orders
    state["clusters"]  = {}
    state["clustered"] = False
    return jsonify({"status": "ok", "n_orders": len(orders)})


@app.route('/api/couriers/upload', methods=['POST'])
def upload_couriers():
    """Завантажує Excel або CSV з кур'єрами."""
    f = request.files.get('file')
    if not f:
        return jsonify({"error": "Файл не надано"}), 400
    try:
        if f.filename.endswith('.csv'):
            import io, csv
            content = f.read().decode('utf-8')
            reader = csv.DictReader(io.StringIO(content))
            couriers = []
            for i, row in enumerate(reader):
                required = ['courier_id', 'name', 'vehicle_type', 'hub_id', 'max_weight', 'max_dist_km', 'min_price', 'lat', 'lon']
                if not all(col in row.keys() for col in required):
                    return jsonify({"error": f"Відсутні колонки: {required}"}), 422
                try:
                    couriers.append({
                        "courier_id":   int(row['courier_id']),
                        "name":         str(row['name']),
                        "vehicle_type": str(row['vehicle_type']),
                        "hub_id":       int(row['hub_id']),
                        "max_weight":   float(row['max_weight']),
                        "max_dist_km":  float(row['max_dist_km']),
                        "min_price":    float(row['min_price']),
                        "lat":          float(row['lat']),
                        "lon":          float(row['lon']),
                    })
                except ValueError as e:
                    return jsonify({"error": f"Рядок {i+2}: {e}"}), 422
        else:
            # Excel
            if f.filename.endswith(('.xlsx', '.xlsm')):
                df = pd.read_excel(f, engine='openpyxl')
            elif f.filename.endswith('.xls'):
                df = pd.read_excel(f, engine='xlrd')
            else:
                return jsonify({"error": "Непідтримуваний формат файлу. Використовуйте .xlsx, .xls або .csv"}), 400
            couriers = []
            required = ['courier_id', 'name', 'vehicle_type', 'hub_id', 'max_weight', 'max_dist_km', 'min_price', 'lat', 'lon']
            if not all(col in df.columns for col in required):
                return jsonify({"error": f"Відсутні колонки: {required}"}), 422
            for i, row in df.iterrows():
                try:
                    couriers.append({
                        "courier_id":   int(row['courier_id']),
                        "name":         str(row['name']),
                        "vehicle_type": str(row['vehicle_type']),
                        "hub_id":       int(row['hub_id']),
                        "max_weight":   float(row['max_weight']),
                        "max_dist_km":  float(row['max_dist_km']),
                        "min_price":    float(row['min_price']),
                        "lat":          float(row['lat']),
                        "lon":          float(row['lon']),
                    })
                except ValueError as e:
                    return jsonify({"error": f"Рядок {i+2}: {e}"}), 422
    except Exception as e:
        return jsonify({"error": f"Помилка читання файлу: {str(e)}"}), 400

    state["couriers"] = couriers
    return jsonify({"status": "ok", "n_couriers": len(couriers)})


@app.route('/api/state', methods=['GET'])
def get_state():
    return jsonify({
        "hubs":      state["hubs"],
        "orders":    state["orders"],
        "couriers":  state["couriers"],
        "clusters":  state["clusters"],
        "clustered": state["clustered"]
    })


# ─────────────────────────────────────────────
# ДИСПЕТЧЕР: кластеризація
# ─────────────────────────────────────────────

@app.route('/api/cluster', methods=['POST'])
def cluster():
    if not state["orders"]:
        return jsonify({"error": "Спочатку згенеруйте або завантажте дані"}), 400

    params    = request.get_json(force=True)
    algorithm = params.get('algorithm', 'kmeans')
    orders    = state["orders"]
    hubs      = state["hubs"]

    if algorithm == 'kmeans':
        result = run_kmeans(orders, hubs)
    elif algorithm == 'dbscan':
        eps     = float(params.get('eps', 0.05))
        min_pts = int(params.get('min_pts', 3))
        result  = run_dbscan(orders, hubs, eps, min_pts)
    elif algorithm == 'optics':
        min_pts = int(params.get('min_pts', 3))
        result  = run_optics(orders, hubs, min_pts)
    else:
        return jsonify({"error": "Невідомий алгоритм"}), 400

    # Update orders with hub assignments
    hub_map = {o['order_id']: o for o in state["orders"]}
    for order_id, hub_id in result["assignments"].items():
        if order_id in hub_map:
            hub_map[order_id]["hub_id"] = hub_id
            hub_map[order_id]["status"] = "Вільне" if hub_id is not None else "Аномалія"

    # Build clusters dict
    clusters = {}
    for hub in hubs:
        clusters[str(hub["hub_id"])] = []
    clusters["noise"] = []
    for order in state["orders"]:
        hid = order.get("hub_id")
        if hid is None:
            clusters["noise"].append(order["order_id"])
        else:
            clusters[str(hid)].append(order["order_id"])

    state["clusters"]  = clusters
    state["clustered"] = True

    return jsonify({
        "status":     "ok",
        "algorithm":  algorithm,
        "clusters":   clusters,
        "noise_count": len(clusters.get("noise", [])),
        "wcss":       result.get("wcss"),
        "exec_ms":    result.get("exec_ms")
    })


# ─────────────────────────────────────────────
# КУР'ЄР: фільтрація
# ─────────────────────────────────────────────

@app.route('/api/courier/orders', methods=['POST'])
def courier_orders():
    """Повертає замовлення для кур'єра з фільтрацією."""
    params     = request.get_json(force=True)
    hub_id     = params.get('hub_id')          # якщо None — всі хаби
    max_weight = params.get('max_weight')
    min_price  = params.get('min_price')
    max_price  = params.get('max_price')
    max_dist   = params.get('max_dist')        # км від хабу

    orders = [o for o in state["orders"] if o["status"] == "Вільне"]
    if hub_id is not None:
        orders = [o for o in orders if o.get("hub_id") == hub_id]

    hub_coords = None
    if hub_id is not None:
        hub = next((h for h in state["hubs"] if h["hub_id"] == hub_id), None)
        if hub:
            hub_coords = (hub["lat"], hub["lon"])

    filtered = filter_orders(orders, max_weight=max_weight, min_price=min_price, max_price=max_price,
                             max_dist_km=max_dist, hub_coords=hub_coords)
    return jsonify({"orders": filtered, "count": len(filtered)})


@app.route('/api/courier/accept', methods=['POST'])
def accept_order():
    """Кур'єр приймає замовлення."""
    params     = request.get_json(force=True)
    order_id   = params.get('order_id')
    courier_id = params.get('courier_id', 1)

    order = next((o for o in state["orders"] if o["order_id"] == order_id), None)
    if not order:
        return jsonify({"error": "Замовлення не знайдено"}), 404
    if order["status"] != "Вільне":
        return jsonify({"error": f"Замовлення вже має статус «{order['status']}»"}), 409

    order["status"]     = "В роботі"
    order["courier_id"] = courier_id
    return jsonify({"status": "ok", "order": order})


@app.route('/api/courier/complete', methods=['POST'])
def complete_order():
    """Кур'єр виконав замовлення."""
    params   = request.get_json(force=True)
    order_id = params.get('order_id')
    order = next((o for o in state["orders"] if o["order_id"] == order_id), None)
    if not order:
        return jsonify({"error": "Замовлення не знайдено"}), 404
    order["status"] = "Виконано"
    return jsonify({"status": "ok", "order": order})


# ─────────────────────────────────────────────
# ДИСПЕТЧЕР: статистика
# ─────────────────────────────────────────────

@app.route('/api/stats', methods=['GET'])
def stats():
    orders = state["orders"]
    total    = len(orders)
    free     = sum(1 for o in orders if o["status"] == "Вільне")
    in_work  = sum(1 for o in orders if o["status"] == "В роботі")
    done     = sum(1 for o in orders if o["status"] == "Виконано")
    noise    = sum(1 for o in orders if o["status"] == "Аномалія")
    return jsonify({
        "total": total, "free": free,
        "in_work": in_work, "done": done, "noise": noise
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Сервер запущено: http://localhost:{port}")
    app.run(debug=True, port=port, host='0.0.0.0')
