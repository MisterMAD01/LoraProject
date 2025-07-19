from flask import Flask, request, render_template_string, send_file
import threading
import csv
import os
import io
import time
import socket
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pickle
import numpy as np

app = Flask(__name__)

current = {"active": False}  # สถานะเปิด/ปิดแสดงจุด
history_rows = []  # โหลดข้อมูล CSV ไว้ (ถ้าใช้)
latest_values = {}  # ค่าล่าสุดที่รับจาก UDP หรือโมเดลทำนาย

udp_status = {"active": False}
last_udp_time = 0

model = None  # โมเดลสำหรับทำนาย

# สร้าง dict เก็บ history RSSI แต่ละตัว
history = {
    'tx1': [],
    'tx2': [],
    'tx3': [],
    'tx4': [],
    'wifi1': [],
    'wifi2': [],
    'wifi3': [],
    'wifi4': [],
    'wifi5': [],
    'wifi6': [],
}

MAX_HISTORY_LEN = 50  # เก็บแค่ 50 จุดล่าสุด


# โหลดโมเดลจากไฟล์ตอนเริ่ม
def load_model():
    global model
    model_path = os.path.join("model", "model11.pkl")
    if os.path.exists(model_path):
        with open(model_path, "rb") as f:
            model = pickle.load(f)
        print("✅ Loaded ML model from model11.pkl")
    else:
        print("❌ Model file not found:", model_path)


# UDP Server Thread รับข้อมูล
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
            # รับข้อมูลรูปแบบ "tx1: -45"
            if ":" in msg:
                label, val = [x.strip().lower() for x in msg.split(":")]
                if label in data_row:
                    try:
                        data_row[label] = float(val)
                    except:
                        pass

            latest_values = data_row.copy()

            # เก็บ history ของทุก key
            for k in history.keys():
                v = data_row.get(k)
                if v is None:
                    # ถ้าไม่มีค่า ให้เก็บ NaN เพื่อไม่ให้กราฟขาด
                    v = np.nan
                history[k].append(v)
                if len(history[k]) > MAX_HISTORY_LEN:
                    history[k].pop(0)

        except socket.timeout:
            if time.time() - last_udp_time > 3:
                udp_status["active"] = False


# ฟังก์ชันทำนายตำแหน่ง x,y ด้วยโมเดล
def predict_position():
    global latest_values, model
    if model is None:
        return None, None

    # เตรียมข้อมูล features จาก latest_values ตามที่โมเดลต้องการ
    features = []
    keys_order = ['tx1', 'tx2', 'tx3', 'tx4', 'wifi1', 'wifi2', 'wifi3', 'wifi4', 'wifi5', 'wifi6']
    for k in keys_order:
        v = latest_values.get(k)
        if v is None:
            v = 0.0
        features.append(float(v))

    X = np.array(features).reshape(1, -1)
    pred = model.predict(X)
    # สมมติโมเดลทำนายตำแหน่ง (x,y) ออกมาเป็น array เช่น [x,y]
    if len(pred.shape) == 2 and pred.shape[1] == 2:
        return int(pred[0][0]), int(pred[0][1])
    else:
        return None, None


# หน้าเว็บหลัก
@app.route("/")
def index():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>ตำแหน่งอุปกรณ์</title>
        <style>
            body { font-family: Arial; background: #f0f0f0; padding: 20px; }
            .container { background: white; padding: 20px; border-radius: 10px; max-width: 700px; margin: auto; box-shadow: 0 0 10px rgba(0,0,0,0.2); }
            h2 { color: #333; }
            button { font-size: 16px; padding: 10px 20px; margin-top: 10px; border: none; border-radius: 5px; cursor: pointer; }
            .start { background: #28a745; color: white; }
            .stop { background: #dc3545; color: white; }
            img { max-width: 100%; border: 1px solid #ccc; margin-top: 20px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>📍 ตำแหน่งที่ทำนายจากโมเดล</h2>

            <form action="/toggle" method="post">
                <button class="{{ 'stop' if active else 'start' }}">
                    {{ '⏹ หยุดแสดงตำแหน่ง' if active else '▶️ เริ่มแสดงตำแหน่ง' }}
                </button>
            </form>

            <p>สถานะ UDP: <strong style="color: {{ 'green' if udp_active else 'red' }}">{{ 'เชื่อมต่อแล้ว' if udp_active else 'รอข้อมูล...' }}</strong></p>

            <img src="/plot" alt="แผนที่" id="mapimg">

            <h2>📈 กราฟเส้นประวัติ RSSI (tx1-4, wifi1-6)</h2>
            <img src="/lineplot" alt="กราฟเส้น RSSI" style="width:100%; max-width:700px; border:1px solid #ccc;">

        </div>

        <script>
          function reloadMap() {
            const img = document.getElementById('mapimg');
            img.src = '/plot?' + new Date().getTime();
          }

          {% if active %}
          setInterval(reloadMap, 2000);
          {% endif %}
        </script>
    </body>
    </html>
    """
    return render_template_string(html,
                                  active=current["active"],
                                  udp_active=udp_status["active"])


# ปุ่ม toggle start/stop แสดงจุด
@app.route("/toggle", methods=["POST"])
def toggle():
    current["active"] = not current["active"]
    return index()


# เสิร์ฟรูปแผนที่ พร้อมจุดทำนาย (ถ้าเปิดแสดง)
@app.route("/plot")
def plot():
    img_path = os.path.join("map", "map.jpg")
    if not os.path.exists(img_path):
        return "ไม่พบไฟล์รูปแผนที่", 404

    img = plt.imread(img_path)
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.imshow(img)

    # ถ้าเปิดแสดง ให้ทำนายตำแหน่งและ plot จุดบนแผนที่
    if current["active"]:
        x, y = predict_position()
        if x is not None and y is not None:
            ax.plot(x, y, 'ro', markersize=10, alpha=0.8)
            ax.text(x + 5, y, f"({x},{y})", color='red', fontsize=12)

    ax.axis('off')
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)
    return send_file(buf, mimetype='image/png')


# เสิร์ฟกราฟเส้นประวัติ RSSI ของทุกตัว
@app.route("/lineplot")
def lineplot():
    fig, ax = plt.subplots(figsize=(10, 5))

    colors = {
        'tx1': 'red',
        'tx2': 'blue',
        'tx3': 'green',
        'tx4': 'purple',
        'wifi1': 'orange',
        'wifi2': 'brown',
        'wifi3': 'pink',
        'wifi4': 'cyan',
        'wifi5': 'magenta',
        'wifi6': 'gray',
    }

    plotted_any = False
    for key, vals in history.items():
        if vals:
            ax.plot(vals, label=key, color=colors.get(key, None))
            plotted_any = True

    ax.set_ylim(-100, 0)  # RSSI ช่วงปกติ (dBm)
    ax.set_title("RSSI History for tx1-4 and wifi1-6")
    ax.set_xlabel("Time (latest to oldest)")
    ax.set_ylabel("RSSI (dBm)")
    ax.legend()
    ax.grid(True)

    if not plotted_any:
        ax.text(0.5, 0.5, "No data yet", ha='center', va='center', fontsize=14)
        ax.axis('off')

    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)
    return send_file(buf, mimetype='image/png')


if __name__ == "__main__":
    os.makedirs("model", exist_ok=True)
    os.makedirs("map", exist_ok=True)

    load_model()

    threading.Thread(target=udp_server, daemon=True).start()

    app.run(host="0.0.0.0", port=1000)
