# app.py
from flask import Flask, request, jsonify, send_file, Response
import time
import csv
from flask import Flask, request, jsonify, send_file, Response
import time
import csv
import os
import re
from datetime import datetime
import glob
import json
import threading
import io

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HTTP_HOST = '0.0.0.0'
HTTP_PORT = 5000

CSV_WRITE_INTERVAL = 5        # shorter for testing; increase later
MAX_CSV_FILES = 5
DATA_CHECK_DELAY = 0.1

CSV_FILENAME_PREFIX = "co2_data_"
CSV_FILE_EXTENSION = ".csv"

app = Flask(__name__)


app = Flask(__name__)

# ---------- CO2 CSV helpers ----------

def get_next_file_number():
    pattern = f"{CSV_FILENAME_PREFIX}*{CSV_FILE_EXTENSION}"
    existing_files = glob.glob(pattern)
    if not existing_files:
        return 1
    numbers = []
    # Regex to extract trailing number in filename co2_data_<n>.csv
    regex_pattern = f'{re.escape(CSV_FILENAME_PREFIX)}(\\d+){re.escape(CSV_FILE_EXTENSION)}'
    for file in existing_files:
        match = re.search(regex_pattern, os.path.basename(file))
        if match:
            numbers.append(int(match.group(1)))
    return max(numbers) + 1 if numbers else 1

def cleanup_old_files():
    pattern = f"{CSV_FILENAME_PREFIX}*{CSV_FILE_EXTENSION}"
    existing_files = glob.glob(pattern)
    if len(existing_files) >= MAX_CSV_FILES:
        file_times = [(f, os.path.getctime(f)) for f in existing_files]
        file_times.sort(key=lambda x: x[1])  # oldest first
        while len(file_times) >= MAX_CSV_FILES:
            os.remove(file_times[0][0])
            file_times.pop(0)

def parse_co2_value(esp32_data):
    """
    esp32_data JSON example:
    {"ts": "2026-02-10T23:15:42", "int_10": 1234.5,
     "temp_c": 21.37, "mac": "AA:BB:CC:DD:EE:FF"}
    """
    try:
        data = json.loads(esp32_data)
        co2_val = float(data.get('int_10', 0.0))
        mac_addr = data.get('mac', '')
        temp_c = data.get('temp_c')  # may be None if not sent
        ts = data.get('ts')

        # If no timestamp provided, fall back to server time
        if ts:
            try:
                # Ensure it parses; store as ISO string
                timestamp = datetime.fromisoformat(ts).isoformat()
            except ValueError:
                timestamp = datetime.now().isoformat()
        else:
            timestamp = datetime.now().isoformat()

        return {"timestamp": timestamp,
                "co2_ppm": co2_val,
                "temp_c": temp_c,
                "mac_address": mac_addr}
    except (json.JSONDecodeError, ValueError, KeyError):
        return None


# ---------- Web UI: main page ----------

@app.route("/")
def index():
    # Airflow control UI + image tags for CO2 & Temperature plots
    html = """
    <!DOCTYPE html>
    <html>
    <head>
      <title>Building Testbed Control</title>
      <style>
        body {
          font-family: Arial;
          display: flex;
          justify-content: center;
          align-items: flex-start;
          min-height: 100vh;
          margin: 0;
          background-color: #f5f5f5;
          padding-top: 20px;
        }
        .page {
          width: 100%;
          max-width: 1100px;
        }
        h1 {
          text-align: center;
          margin-bottom: 40px;
        }

        .grid-container {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          grid-gap: 40px;
        }
        .card {
          background-color: #fff;
          border: 1px solid #ccc;
          padding: 25px;
          text-align: center;
          border-radius: 12px;
          box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }

        .slider-container {
          display: flex;
          align-items: center;
          gap: 12px;
          margin: 15px 0;
        }
        input[type="range"] {
          flex: 1;
        }
        .value {
          min-width: 40px;
          font-weight: bold;
        }

        /* Metrics row for CO2 and Temperature, matching the card look */
        .metrics-row {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          grid-gap: 40px;
          margin-top: 40px;
        }
        .metric-card {
          background-color: #fff;
          border-radius: 12px;
          padding: 20px;
          box-shadow: 0 4px 8px rgba(0,0,0,0.1);
          border: 1px solid #ccc;
          text-align: center;
        }
        .metric-card h3 {
          margin-top: 0;
          margin-bottom: 10px;
        }
        .metric-card p {
          margin-top: 0;
          margin-bottom: 15px;
          color: #555;
          font-size: 0.9rem;
        }
        .metric-card img {
          max-width: 100%;
          height: auto;
          border-radius: 8px;
          border: 1px solid #eee;
        }
      </style>
    </head>
    <body>
    <div class="page">
      <h1>Airflow & CO₂ Control Panel</h1>

      <div class="grid-container">
        <div class="card">
          <h3>Inlet Fan</h3>
          <div class="slider-container">
            <input type="range" min="0" max="100" id="inletFan" value="0">
            <span class="value" id="inletFanValue">0%</span>
          </div>
          <button onclick="setFan('inlet')">Apply</button>
        </div>

        <div class="card">
          <h3>Outlet Fan</h3>
          <div class="slider-container">
            <input type="range" min="0" max="100" id="outletFan" value="0">
            <span class="value" id="outletFanValue">0%</span>
          </div>
          <button onclick="setFan('outlet')">Apply</button>
        </div>

        <div class="card">
          <h3>Inlet Vent</h3>
          <div class="slider-container">
            <input type="range" min="0" max="70" id="inletVent" value="0">
            <span class="value" id="inletVentValue">0deg</span>
          </div>
          <button onclick="setVent('inlet')">Apply</button>
        </div>

        <div class="card">
          <h3>Outlet Vent</h3>
          <div class="slider-container">
            <input type="range" min="0" max="70" id="outletVent" value="0">
            <span class="value" id="outletVentValue">0deg</span>
          </div>
          <button onclick="setVent('outlet')">Apply</button>
        </div>
      </div>

      <!-- New metrics row: CO2 (left) and Temperature (right) -->
      <div class="metrics-row">
        <div class="metric-card">
          <h3>CO₂ vs Time</h3>
          <p>Plot is regenerated on each page load from co2_data_*.csv.</p>
          <img src="/plot.png?ts=TIMESTAMP_PLACEHOLDER" alt="CO2 plot">
        </div>

        <div class="metric-card">
          <h3>Temperature vs Time</h3>
          <p>Temperature data is captured along with CO₂ and can be plotted here.</p>
          <!-- For now this uses the same endpoint; replace with /temp_plot.png when you add it -->
          <img src="/plot.png?kind=temp&ts=TIMESTAMP_PLACEHOLDER" alt="Temperature plot">
        </div>
      </div>
    </div>

    <script>
    function setFan(fan) {
      const speed = document.getElementById(fan + 'Fan').value;
      fetch('/fan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fan: fan, speed: Number(speed) })
      });
    }

    function setVent(vent) {
      const angle = document.getElementById(vent + 'Vent').value;
      fetch('/vent', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ vent: vent, angle: Number(angle) })
      });
    }

    function initSlider(id, unit) {
      const slider = document.getElementById(id);
      const label = document.getElementById(id + "Value");
      slider.value = 0;
      label.textContent = "0" + unit;
      slider.oninput = () => {
        label.textContent = slider.value + unit;
      };
    }

    window.onload = () => {
      initSlider("inletFan", "%");
      initSlider("outletFan", "%");
      initSlider("inletVent", "deg");
      initSlider("outletVent", "deg");

      // bust cache on plots
      const now = new Date().getTime();
      const co2Img = document.querySelectorAll('.metric-card img')[0];
      const tempImg = document.querySelectorAll('.metric-card img')[1];

      co2Img.src = '/plot.png?ts=' + now;
      tempImg.src = '/plot.png?kind=temp&ts=' + now; // change endpoint when you add temp plot
    };
    </script>
    </body>
    </html>
    """
    return Response(html, mimetype="text/html")

   
# ---------- API: fans/vents ----------

@app.route("/fan", methods=["POST"])
def set_fan():
    data = request.get_json(force=True, silent=True) or {}
    fan = data.get("fan")
    speed = data.get("speed")
    print(f"Set fan {fan} to {speed}")
    # TODO: call your hardware control here
    return jsonify(status="ok")

@app.route("/vent", methods=["POST"])
def set_vent():
    data = request.get_json(force=True, silent=True) or {}
    vent = data.get("vent")
    angle = data.get("angle")
    print(f"Set vent {vent} to {angle}")
    # TODO: call your hardware control here
    return jsonify(status="ok")
  
  
# ---------- CO2 plot endpoint ----------

@app.route("/plot.png")
def plot_png():
    pattern = f"{CSV_FILENAME_PREFIX}*{CSV_FILE_EXTENSION}"
    csv_files = glob.glob(pattern)

    dfs = []

    # Load CSV data if any
    for f in csv_files:
        df = pd.read_csv(f)
        df = df.rename(columns={
            "co2ppm": "co2_ppm",
            "macaddress": "mac_address"
        })
        dfs.append(df)

    # Also include current in-memory buffer so you see latest point
    if not dfs:
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.text(0.5, 0.5, "No CO2 data yet", ha="center", va="center")
        ax.axis("off")
    else:
        co2_all = pd.concat(dfs, ignore_index=True)
        co2_all["timestamp"] = pd.to_datetime(co2_all["timestamp"])

        unique_macs = co2_all["mac_address"].unique()
        color_cycle = [
            'darkorchid', 'blue', 'orange', 'red', 'green', 'cyan',
            'indigo', 'magenta', 'lightcoral', 'orangered', 'burlywood',
            'gold', 'yellowgreen', 'cadetblue', 'skyblue'
        ]
        mac_to_color = {
            mac: color_cycle[i % len(color_cycle)]
            for i, mac in enumerate(unique_macs)
        }

        fig, ax = plt.subplots(figsize=(10, 4))
        for mac in unique_macs:
            df_mac = co2_all[co2_all["mac_address"] == mac]
            ax.scatter(
                df_mac["timestamp"],
                df_mac["co2_ppm"],
                s=8,
                color=mac_to_color[mac],
                alpha=0.7,
                label=mac
            )
        ax.set_xlabel("Time")
        ax.set_ylabel("CO₂ (ppm)")
        ax.set_title("CO₂ vs Time")
        ax.legend(markerscale=2, fontsize=8)
        fig.autofmt_xdate()
        fig.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    plt.close()
    buf.seek(0)
    return send_file(buf, mimetype="image/png")

# ---------- Main ----------

def main():
    print(f"Starting CO2 server on {HTTP_HOST}:{HTTP_PORT}")
    app.run(host=HTTP_HOST, port=HTTP_PORT, debug=False)

if __name__ == "__main__":
    main()
