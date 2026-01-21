from flask import Flask, request, jsonify
import RPi.GPIO as GPIO
import atexit
import requests

# =======================
# GPIO FAN SETUP (PI)
# =======================
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

INLET_FAN_PIN = 18
OUTLET_FAN_PIN = 13
PWM_FREQ = 1000

GPIO.setup(INLET_FAN_PIN, GPIO.OUT)
GPIO.setup(OUTLET_FAN_PIN, GPIO.OUT)

inlet_pwm = GPIO.PWM(INLET_FAN_PIN, PWM_FREQ)
outlet_pwm = GPIO.PWM(OUTLET_FAN_PIN, PWM_FREQ)

inlet_pwm.start(0)
outlet_pwm.start(0)

# =======================
# ESP32 CONFIG
# =======================
#ESP32_BASE_URL = "http://esp32.local"   # change to IP if needed
ESP32_BASE_URL = "http://100.84.23.203"
VENT_ENDPOINT = f"{ESP32_BASE_URL}/vent"

# =======================
# FLASK APP
# =======================
app = Flask(__name__, static_folder="static")

# =======================
# SAFETY CLEANUP
# =======================
def cleanup_gpio():
    inlet_pwm.ChangeDutyCycle(0)
    outlet_pwm.ChangeDutyCycle(0)
    inlet_pwm.stop()
    outlet_pwm.stop()
    GPIO.cleanup()
    print("GPIO cleaned up")

atexit.register(cleanup_gpio)

# =======================
# ROUTES
# =======================
@app.route("/")
def index():
    return app.send_static_file("index.html")

# -----------------------
# FAN CONTROL (PI)
# -----------------------
@app.route("/fan", methods=["POST"])
def fan_control():
    data = request.json

    fan = data.get("fan")        # inlet | outlet
    speed = int(data.get("speed", 0))

    speed = max(0, min(speed, 100))  # safety clamp

    if fan == "inlet":
        inlet_pwm.ChangeDutyCycle(speed)
    elif fan == "outlet":
        outlet_pwm.ChangeDutyCycle(speed)
    else:
        return jsonify(error="Invalid fan"), 400

    print(f"[USER] {fan.upper()} FAN ? {speed}%")
    return jsonify(ok=True)

# -----------------------
# VENT CONTROL (ESP32)
# -----------------------
@app.route("/vent", methods=["POST"])
def vent_control():
    data = request.json

    vent = data.get("vent")          # inlet | outlet
    angle = int(data.get("angle", 0))

    angle = max(0, min(angle, 180))  # safety clamp

    payload = {
        "vent": vent,
        "angle": angle
    }

    try:
        r = requests.post(VENT_ENDPOINT, json=payload, timeout=1.0)
        r.raise_for_status()
        print(f"[USER] {vent.upper()} VENT -> {angle} degrees")
        return jsonify(ok=True)

    except requests.RequestException as e:
        print(f"ERROR] ESP32 not reachable: {e}")
        return jsonify(error="ESP32 communication failed"), 500

# =======================
# MAIN
# =======================
if __name__ == "__main__":
    print("Starting room control server on 0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
