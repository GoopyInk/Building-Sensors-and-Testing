from flask import Flask, request, jsonify
import json
import sqlite3
from datetime import datetime, timedelta, timezone
import time
app = Flask(__name__)
time.sleep(30)


connection = sqlite3.connect("Sensor.db", check_same_thread=False)
cursor = connection.cursor()


@app.route("/")
def index():
    return "<p>Hello World, From Pi!</p>"


@app.route('/echo', methods=['GET', 'POST'])
def echo():
    if request.method == 'POST':
        dataIncoming = json.loads(request.values['esp32'])
        print(dataIncoming)
        return jsonify('success'), 200


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
