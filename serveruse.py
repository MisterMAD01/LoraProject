from flask import Flask, request, render_template_string, send_file, redirect, jsonify
import threading
import csv
import os
import io
import time
import socket
import joblib as jb
import numpy as np

app = Flask(__name__)

last_labels = []
current = {"active": False}
history_rows = []
latest_values = {}

udp_status = {"active": False}
last_udp_time = 0

model = None

history = {
    'tx1': [], 'tx2': [], 'tx3': [], 'tx4': [],
    'wifi1': [], 'wifi2': [], 'wifi3': [], 'wifi4': [], 'wifi5': [], 'wifi6': []
}

MAX_HISTORY_LEN = 50

label_encoder = None

def load_model():
    global model, label_encoder
    base_dir = os.path.dirname(os.path.abspath(__file__))  # <<-- Path ของไฟล์นี้

    model_path = os.path.join(base_dir, "knn.pkl")
    encoder_path = os.path.join(base_dir, "label_encoder.pkl")

    
    if os.path.exists(model_path):
        model = jb.load(model_path)
        print("✅ Loaded ML model from bestparaknn.pkl")
    else:
        print("❌ Model file not found:", model_path)
    
    if os.path.exists(encoder_path):
        label_encoder = jb.load(encoder_path)
        print("✅ Loaded Label Encoder")
    else:
        print("⚠️ Label encoder not found")



def udp_server():
    global last_udp_time, latest_values, udp_status, history
    UDP_IP = "0.0.0.0"
    UDP_PORT = 2500
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind((UDP_IP, UDP_PORT))
    except OSError:
        print(f"❌ Port {UDP_PORT} already in use!")
        return
    print(f"📡 Listening on UDP port {UDP_PORT}")

    data_row = {f"tx{i}": None for i in range(1, 5)}
    data_row.update({f"wifi{i}": 0.0 for i in range(1, 7)})

    while True:
        sock.settimeout(1.0)
        try:
            data, _ = sock.recvfrom(1024)
            msg = data.decode().strip()
            udp_status["active"] = True
            last_udp_time = time.time()
            if ":" in msg:
                label, val = [x.strip().lower() for x in msg.split(":")]
                if label in data_row:
                    try:
                        data_row[label] = float(val)
                    except:
                        pass
            latest_values = data_row.copy()
            for k in history.keys():
                v = data_row.get(k)
                if v is None:
                    v = np.nan
                history[k].append(v)
                if len(history[k]) > MAX_HISTORY_LEN:
                    history[k].pop(0)
        except socket.timeout:
            if time.time() - last_udp_time > 3:
                udp_status["active"] = False

location_map = {
    "A1": (140, 239),
    "A10": (396, 237),
    "A11": (419, 237),
    "A12": (451, 237),
    "A13": (481, 237),
    "A14": (503, 237),
    "A15": (532, 237),
    "A16": (563, 237),
    "A17": (586, 237),
    "A18": (616, 237),
    "A19": (647, 237),
    "A2": (167, 237),
    "A20": (674, 237),
    "A21": (704, 237),
    "A22": (733, 237),
    "A23": (751, 237),
    "A24": (780, 237),
    "A25": (813, 237),
    "A26": (840, 237),
    "A27": (865, 237),
    "A28": (896, 237),
    "A29": (925, 237),
    "A3": (197, 239),
    "A30": (957, 237),
    "A31": (986, 237),
    "A32": (1012, 237),
    "A33": (1042, 237),
    "A34": (1073, 237),
    "A35": (1096, 237),
    "A36": (1124, 239),
    "A37": (1157, 239),
    "A38": (1178, 239),
    "A39": (1203, 239),
    "A4": (219, 237),
    "A40": (1237, 239),
    "A5": (249, 237),
    "A6": (283, 237),
    "A7": (311, 237),
    "A8": (333, 237),
    "A9": (365, 237),
    "B1": (139, 272),
    "B17": (582, 272),
    "B18": (619, 272),
    "B19": (643, 272),
    "B2": (169, 272),
    "B20": (673, 255),
    "B21": (696, 272),
    "B22": (727, 272),
    "B23": (755, 272),
    "B24": (783, 272),
    "B39": (1205, 275),
    "B40": (1237, 275),
    "C1": (135, 303),
    "C17": (585, 303),
    "C18": (617, 303),
    "C19": (641, 303),
    "C2": (167, 303),
    "C20": (672, 303),
    "C21": (696, 303),
    "C22": (727, 303),
    "C23": (758, 303),
    "C24": (784, 303),
    "C39": (1205, 303),
    "C40": (1233, 303),
    "D1": (141, 340),
    "D17": (586, 339),
    "D18": (613, 339),
    "D19": (642, 339),
    "D2": (165, 340),
    "D20": (672, 339),
    "D21": (691, 339),
    "D22": (726, 339),
    "D23": (759, 339),
    "D24": (788, 339),
    "D39": (1203, 334),
    "D40": (1233, 334),
    "E1": (136, 370),
    "E17": (587, 370),
    "E18": (610, 370),
    "E19": (642, 370),
    "E2": (161, 370),
    "E20": (667, 370),
    "E21": (696, 370),
    "E22": (730, 370),
    "E23": (759, 370),
    "E24": (788, 370),
    "E39": (1203, 370),
    "E40": (1237, 370),
    "F1": (139, 400),
    "F17": (588, 400),
    "F18": (613, 400),
    "F19": (644, 383),
    "F2": (165, 400),
    "F20": (675, 400),
    "F21": (696, 400),
    "F22": (729, 400),
    "F23": (755, 400),
    "F24": (788, 400),
    "F39": (1205, 400),
    "F40": (1237, 400),
    "G1": (139, 430),
    "G10": (387, 430),
    "G11": (422, 430),
    "G12": (448, 430),
    "G13": (479, 430),
    "G14": (502, 430),
    "G15": (536, 430),
    "G16": (557, 430),
    "G17": (588, 430),
    "G18": (620, 430),
    "G19": (642, 430),
    "G2": (167, 430),
    "G20": (676, 430),
    "G21": (701, 430),
    "G22": (732, 430),
    "G23": (763, 430),
    "G24": (788, 430),
    "G25": (314, 430),
    "G26": (846, 430),
    "G27": (873, 430),
    "G28": (898, 430),
    "G29": (930, 430),
    "G3": (195, 430),
    "G30": (955, 430),
    "G31": (982, 430),
    "G32": (1014, 430),
    "G33": (1042, 430),
    "G34": (1068, 430),
    "G35": (1093, 430),
    "G36": (1122, 430),
    "G37": (1152, 430),
    "G38": (1176, 430),
    "G39": (1202, 430),
    "G4": (226, 430),
    "G40": (1231, 430),
    "G5": (255, 430),
    "G6": (281, 430),
    "G7": (307, 430),
    "G8": (341, 430),
    "G9": (363, 430),
}
def smooth_history(key, window=5):
    values = history.get(key, [])
    if len(values) < window:
        return values[-1] if values else 0.0
    return np.mean(values[-window:])

def predict_position():
    global latest_values, model, label_encoder, last_labels
    if model is None or label_encoder is None:
        return None, None, None

    features = [smooth_history(k) for k in [
        'tx1', 'tx2', 'tx3', 'tx4',
        'wifi1', 'wifi2', 'wifi3', 'wifi4', 'wifi5', 'wifi6'
    ]]
    X = np.array(features).reshape(1, -1)

    pred_encoded = model.predict(X)[0]
    label = label_encoder.inverse_transform([pred_encoded])[0]

    last_labels.append(label)
    if len(last_labels) > 3:
        last_labels.pop(0)

    if last_labels.count(label) >= 2:
        x, y = location_map.get(label, (None, None))
        return x, 663 - y if y is not None else None, label
    else:
        return None, None, None


@app.route("/")
def index():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>ตำแหน่งอุปกรณ์ (Indoor)</title>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.3/dist/leaflet.css" />
        <style>
            #map { height: 80vh; border: 1px solid #ccc; }
            .control { padding: 10px; background: #fff; }
        </style>
    </head>
    <body>
        <div class="control">
            <form action="/toggle" method="post" style="display:inline;">
                <button type="submit">{{ '⏹ หยุดแสดงตำแหน่ง' if active else '▶️ เริ่มแสดงตำแหน่ง' }}</button>
            </form>
            <span>สถานะ UDP: <strong style="color: {{ 'green' if udp_active else 'red' }}">{{ 'เชื่อมต่อแล้ว' if udp_active else 'รอข้อมูล...' }}</strong></span>
        </div>
        <div class="control">
    พิกัดเมาส์: <span id="mouse-coords">(x, y)</span>
    <p>ตำแหน่งทำนายล่าสุด: <span id="predicted-label">–</span></p>

</div>

        <div id="map"></div>

<script src="https://unpkg.com/leaflet@1.9.3/dist/leaflet.js"></script>
<script>
const bounds = [[0, 0], [663, 1366]]; // [[y1,x1], [y2,x2]]
const map = L.map('map', {
    crs: L.CRS.Simple,
    minZoom: -1
});
const image = L.imageOverlay('/static/map.jpg', bounds).addTo(map);
map.fitBounds(bounds);

const pixelsPerMeterX = 1366 / 58;
const pixelsPerMeterY = 663 / 30;

let marker = null;

// ✅ แสดง marker จากตำแหน่งทำนาย
async function updateMarker() {
    const res = await fetch("/api/position");
    const data = await res.json();

    if (data.x != null && data.y != null) {
        const lat = data.y;
        const lng = data.x;

        if (!marker) {
            marker = L.marker([lat, lng]).addTo(map);
        } else {
            marker.setLatLng([lat, lng]);
        }

        document.getElementById('predicted-label').innerText = data.label || "–";

        const x_meter = data.x / pixelsPerMeterX;
        const y_meter = data.y / pixelsPerMeterY;
        document.getElementById('predicted-coords').innerText = `x ≈ ${x_meter.toFixed(2)} ม., y ≈ ${y_meter.toFixed(2)} ม.`;
    }
}

map.on('mousemove', function(e) {
    const lat = e.latlng.lat;
    const lng = e.latlng.lng;
    const x_meter = lng / pixelsPerMeterX;
    const y_meter = lat / pixelsPerMeterY;
    document.getElementById('mouse-coords').innerText = `x ≈ ${x_meter.toFixed(2)} ม., y ≈ ${y_meter.toFixed(2)} ม.`;
});

// ✅ เรียกทุก 2 วินาที (เฉพาะตอน active)
{% if active %}
setInterval(updateMarker, 2000);
{% endif %}
</script>

    </body>
    </html>
    """
    return render_template_string(html, active=current["active"], udp_active=udp_status["active"])

@app.route("/toggle", methods=["POST"])
def toggle():
    current["active"] = not current["active"]
    return redirect("/")

@app.route("/api/position")
def api_position():
    x, y, label = predict_position()
    return jsonify({"x": x, "y": y, "label": label})


if __name__ == "__main__":
    os.makedirs("model", exist_ok=True)
    os.makedirs("static", exist_ok=True)  # map.jpg should be inside /static
    load_model()
    threading.Thread(target=udp_server, daemon=True).start()
    app.run(host="0.0.0.0", port=1000)
