from flask import Flask, request, jsonify
import time
import csv
import os
import re
from datetime import datetime
import glob
import json
import threading

HTTP_HOST = '0.0.0.0'
HTTP_PORT = 5000

CSV_WRITE_INTERVAL = 30
MAX_CSV_FILES = 5
DATA_CHECK_DELAY = 0.1

CSV_FILENAME_PREFIX = "co2_data_"
CSV_FILE_EXTENSION = ".csv"

def get_next_file_number():
    pattern = f"{CSV_FILENAME_PREFIX}*{CSV_FILE_EXTENSION}"
    existing_files = glob.glob(pattern)
    if not existing_files:
        return 1

    numbers = []
    for file in existing_files:
        regex_pattern = f'{re.escape(CSV_FILENAME_PREFIX)}(\\d+){re.escape(CSV_FILE_EXTENSION)}'
        match = re.search(regex_pattern, file)
        if match:
            numbers.append(int(match.group(1)))

    return max(numbers) + 1 if numbers else 1

def cleanup_old_files():
    pattern = f"{CSV_FILENAME_PREFIX}*{CSV_FILE_EXTENSION}"
    existing_files = glob.glob(pattern)
    if len(existing_files) >= MAX_CSV_FILES:
        file_times = [(f, os.path.getctime(f)) for f in existing_files]
        file_times.sort(key=lambda x: x[1])

        while len(file_times) >= MAX_CSV_FILES:
            os.remove(file_times[0][0])
            file_times.pop(0)

app = Flask(__name__)
data_buffer = []
last_write_time = time.time()

def parse_co2_value(esp32_data):
    try:
        data = json.loads(esp32_data)
        if 'int_10' in data:
            return float(data['int_10'])
    except (json.JSONDecodeError, ValueError, KeyError):
        pass
    return None

@app.route('/echo', methods=['POST'])
def echo():
    global data_buffer
    try:
        esp32_data = request.values.get('esp32')
        if esp32_data:
            co2_value = parse_co2_value(esp32_data)
            if co2_value is not None:
                timestamp = datetime.now().isoformat()
                data_buffer.append([timestamp, co2_value])
                print(f"Received CO2: {co2_value} ppm")
        return jsonify('success'), 200
    except Exception as e:
        print(f"Error processing request: {e}")
        return jsonify('error'), 400

def csv_writer_thread():
    global data_buffer, last_write_time

    while True:
        try:
            current_time = time.time()
            if current_time - last_write_time >= CSV_WRITE_INTERVAL:
                if data_buffer:
                    cleanup_old_files()

                    file_number = get_next_file_number()
                    filename = f"{CSV_FILENAME_PREFIX}{file_number}{CSV_FILE_EXTENSION}"

                    data_to_write = data_buffer.copy()
                    data_buffer.clear()

                    with open(filename, 'w', newline='') as csvfile:
                        writer = csv.writer(csvfile)
                        writer.writerow(['timestamp', 'co2_ppm'])
                        writer.writerows(data_to_write)

                    print(f"Wrote {len(data_to_write)} records to {filename}")

                last_write_time = current_time

            time.sleep(DATA_CHECK_DELAY)

        except Exception as e:
            print(f"Error in CSV writer: {e}")
            time.sleep(DATA_CHECK_DELAY)

def main():
    print(f"Starting CO2 data server on {HTTP_HOST}:{HTTP_PORT}")

    csv_thread = threading.Thread(target=csv_writer_thread, daemon=True)
    csv_thread.start()

    try:
        app.run(host=HTTP_HOST, port=HTTP_PORT, debug=False)
    except KeyboardInterrupt:
        print("Stopping CO2 reader...")
    except Exception as e:
        print(f"Server error: {e}")

if __name__ == "__main__":
    main()
