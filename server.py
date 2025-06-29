from flask import Flask, request, render_template_string, jsonify
import socket
import threading
import csv
import time
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
current = {"location": "", "x": "", "y": "", "active": False, "filename": ""}
history_rows = []
udp_status = {"active": False}
last_udp_time = 0

@app.route("/")
def index():
    html = """<!doctype html>
    <html>
    <head>
        <title>LoRa + WiFi Data Logger</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: sans-serif; margin: 10px; }
            input, button { padding: 6px; margin: 5px; width: 95%; font-size: 16px; }
            .status { margin-top: 10px; font-weight: bold; }
            .container { max-width: 700px; margin: auto; background: #f9f9f9; padding: 15px; border-radius: 8px; box-shadow: 0 0 10px #ccc; }
            .scroll-table { margin-top: 20px; overflow-x: auto; border: 1px solid #ddd; max-height: 400px; overflow-y: auto; }
            table { border-collapse: collapse; min-width: 1000px; width: 100%; }
            th, td { border: 1px solid #ccc; padding: 6px 8px; text-align: center; font-size: 13px; }
            thead { background-color: #007bff; color: white; position: sticky; top: 0; }
            tbody tr:nth-child(even) { background-color: #f9f9f9; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>📡 LoRa + WiFi Data Logger</h2>

            {% if not active %}
            <form action="/start" method="post">
                Location:<br><input name="location" value="{{ location }}"><br>
                X:<br><input name="x" value="{{ x }}"><br>
                Y:<br><input name="y" value="{{ y }}"><br>
                <button style="background:#007bff; color:white;">▶️ Start</button>
            </form>
            {% else %}
            <form action="/stop" method="post">
                <button style="background:#dc3545; color:white;">⏹ Stop</button>
            </form>
            {% endif %}

            <div class="status">
                Status: <span id="udp-status" style="font-weight:bold;"></span><br>
                {% if active %}
                    <b>Location:</b> {{ location }} | <b>X:</b> {{ x }} | <b>Y:</b> {{ y }}<br>
                {% endif %}
            </div>

            <div class="scroll-table">
                <table id="data-table">
                    <thead>
                        <tr>
                            <th>Location</th><th>X</th><th>Y</th>
                            <th>TX1</th><th>TX2</th><th>TX3</th><th>TX4</th>
                            <th>WiFi1</th><th>WiFi2</th><th>WiFi3</th>
                            <th>WiFi4</th><th>WiFi5</th><th>WiFi6</th>
                        </tr>
                    </thead>
                    <tbody id="table-body"></tbody>
                </table>
            </div>
        </div>

        <script>
            async function fetchData() {
                const res = await fetch("/latest_all");
                const data = await res.json();
                const body = document.getElementById("table-body");
                body.innerHTML = "";

                for (let row of data) {
                    const tr = document.createElement("tr");
                    for (let cell of row) {
                        const td = document.createElement("td");
                        td.textContent = cell;
                        tr.appendChild(td);
                    }
                    body.appendChild(tr);
                }
            }

            async function fetchUdpStatus() {
                const res = await fetch("/udp_status");
                const data = await res.json();
                const statusSpan = document.getElementById("udp-status");

                if (data.active) {
                    statusSpan.textContent = "Receiving UDP data";
                    statusSpan.style.color = "green";
                } else {
                    statusSpan.textContent = "Waiting for UDP...";
                    statusSpan.style.color = "red";
                }
            }

            setInterval(fetchData, 1000);
            setInterval(fetchUdpStatus, 1000);
            fetchData();
            fetchUdpStatus();
        </script>
    </body>
    </html>"""
    return render_template_string(html,
                                  active=current["active"],
                                  location=current["location"],
                                  x=current["x"],
                                  y=current["y"])

@app.route("/start", methods=["POST"])
def start():
    location = request.form["location"]
    safe_location = secure_filename(location)
    filename = os.path.join("csv", f"{safe_location}.csv")

    # สร้างโฟลเดอร์ csv หากยังไม่มี
    if not os.path.exists("csv"):
        os.makedirs("csv")

    current.update({
        "location": location,
        "x": request.form["x"],
        "y": request.form["y"],
        "active": True,
        "filename": filename
    })
    print("▶️ Started logging:", filename)
    return index()

@app.route("/stop", methods=["POST"])
def stop():
    current["active"] = False
    print("⏹ Stopped logging")
    return index()

@app.route("/latest_all")
def latest_all():
    return jsonify(history_rows)

@app.route("/udp_status")
def udp_status_route():
    return jsonify({"active": udp_status["active"]})

def udp_server():
    global last_udp_time
    UDP_IP = "0.0.0.0"
    UDP_PORT = 2500
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    print(f"📡 Listening on UDP port {UDP_PORT}")

    data_row = {f"tx{i}": None for i in range(1, 5)}
    data_row.update({f"wifi{i}": "0" for i in range(1, 7)})

    filename = None
    f = None
    writer = None

    while True:
        sock.settimeout(1.0)
        try:
            data, _ = sock.recvfrom(1024)
            msg = data.decode().strip()
            udp_status["active"] = True
            last_udp_time = time.time()
            print(f"📥 UDP Received: {msg}")

            if ":" in msg:
                label, rssi = [x.strip().lower() for x in msg.split(":")]
                if label in data_row:
                    data_row[label] = rssi

        except socket.timeout:
            if time.time() - last_udp_time > 3:
                if udp_status["active"]:
                    print("❌ No UDP received in the last 3 seconds.")
                udp_status["active"] = False

        if current["active"] and all(data_row[f"tx{i}"] is not None for i in range(1, 5)):
            if filename != current["filename"]:
                if f:
                    f.close()
                filename = current["filename"]
                file_exists = os.path.exists(filename)
                f = open(filename, "a", newline="")
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(["location", "x", "y"] +
                                    [f"tx{i}" for i in range(1, 5)] +
                                    [f"wifi{i}" for i in range(1, 7)])

            row = [current["location"], current["x"], current["y"]] + \
                  [data_row[f"tx{i}"] for i in range(1, 5)] + \
                  [data_row[f"wifi{i}"] for i in range(1, 7)]

            writer.writerow(row)
            f.flush()
            history_rows.append(row)
            if len(history_rows) > 100:
                history_rows.pop(0)

            print("✅ Row saved:", row)

            # Reset data_row
            for i in range(1, 5):
                data_row[f"tx{i}"] = None
            for i in range(1, 7):
                data_row[f"wifi{i}"] = "0"

if __name__ == "__main__":
    threading.Thread(target=udp_server, daemon=True).start()
    app.run(host="0.0.0.0", port=9000)
