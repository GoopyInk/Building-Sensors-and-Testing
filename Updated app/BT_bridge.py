import requests
import serial

# 1) Change this to the Bluetooth serial device / COM port
# Windows example:  COM6
# macOS example:    "/dev/tty.ESP32_CO2-SerialPort"
# Linux example:    "/dev/rfcomm0"
PORT = "/dev/tty.ESP32_CO2"  # TODO: set correctly
BAUD = 115200

# 2) Flask server URL (same machine)
ECHO_URL = "http://localhost:5000/echo"

def main():
    ser = serial.Serial(PORT, BAUD, timeout=1)
    print(f"Reading from {PORT}, sending to {ECHO_URL}")
    while True:
        line = ser.readline().decode(errors="ignore").strip()
        if not line:
            continue

        print("BT line:", line)
        try:
            # POST as form field "esp32"
            resp = requests.post(ECHO_URL, data={"esp32": line}, timeout=2)
            print("Flask status:", resp.status_code)
        except Exception as e:
            print("Error posting to Flask:", e)

if __name__ == "__main__":
    main()
