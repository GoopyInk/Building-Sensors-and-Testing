import serial
import requests
import json

# Adjust to your OS / port name
# Windows example: "COM7"
# Linux example: "/dev/rfcomm0"
PORT = "COM7"
BAUD = 115200

SERVER_URL = "http://your_server_ip:5000/echo"  # change IP as needed

ser = serial.Serial(PORT, BAUD, timeout=1)

print(f"Listening on {PORT} at {BAUD} baud")

while True:
    line = ser.readline().decode(errors="ignore").strip()
    if not line:
        continue

    # Optional: quick validation / logging
    try:
        data = json.loads(line)
        mac = data.get("mac", "UNKNOWN")
        co2 = data.get("int_10", None)
        print(f"Received from BT - MAC: {mac}, CO2: {co2}")
    except json.JSONDecodeError:
        print("Got non‑JSON line over Bluetooth:", line)
        continue

    try:
        # Server expects form field named "esp32" containing JSON string
        resp = requests.post(SERVER_URL, data={"esp32": line}, timeout=2)
        if resp.status_code != 200:
            print("Server returned status", resp.status_code, resp.text)
    except Exception as e:
        print("Error sending to server:", e)
