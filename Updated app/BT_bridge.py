import time
import serial
import csv
import json
import glob
import os
import re
from datetime import datetime

# ----- Serial config -----
PORT = "/dev/tty.ESP32_CO2"  # make sure this matches your OS/device
BAUD = 115200

# ----- CSV / rotation config -----
CSV_FILENAME_PREFIX = "co2_data_"
CSV_FILE_EXTENSION = ".csv"
MAX_CSV_FILES = 5           # keep at most N CSV files
ROWS_PER_FILE = 1000        # rollover to a new file after this many rows

current_filename = None
current_file = None
current_writer = None
current_rows = 0


def get_next_file_number():
    pattern = f"{CSV_FILENAME_PREFIX}*{CSV_FILE_EXTENSION}"
    existing_files = glob.glob(pattern)
    if not existing_files:
        return 1
    numbers = []
    regex_pattern = f'{re.escape(CSV_FILENAME_PREFIX)}(\\d+){re.escape(CSV_FILE_EXTENSION)}'
    for file in existing_files:
        m = re.search(regex_pattern, os.path.basename(file))
        if m:
            numbers.append(int(m.group(1)))
    return max(numbers) + 1 if numbers else 1


def cleanup_old_files():
    pattern = f"{CSV_FILENAME_PREFIX}*{CSV_FILE_EXTENSION}"
    existing_files = glob.glob(pattern)
    if len(existing_files) <= MAX_CSV_FILES:
        return
    file_times = [(f, os.path.getctime(f)) for f in existing_files]
    file_times.sort(key=lambda x: x[1])  # oldest first
    while len(file_times) > MAX_CSV_FILES:
        oldest, _ = file_times.pop(0)
        try:
            os.remove(oldest)
            print(f"Removed old CSV: {oldest}")
        except Exception as e:
            print(f"Error removing {oldest}: {e}")


def open_new_csv():
    """Close current CSV (if any) and open a new one with header."""
    global current_filename, current_file, current_writer, current_rows

    # Close previous file
    if current_file is not None:
        current_file.close()
        current_file = None
        current_writer = None

    cleanup_old_files()
    file_number = get_next_file_number()
    filename = f"{CSV_FILENAME_PREFIX}{file_number}{CSV_FILE_EXTENSION}"
    f = open(filename, "w", newline="")
    writer = csv.writer(f)
    writer.writerow(["timestamp", "co2_ppm", "temp_c", "mac_address"])
    f.flush()

    current_filename = filename
    current_file = f
    current_writer = writer
    current_rows = 0

    print(f"Opened new CSV file: {filename}")


def ensure_csv_open():
    """Make sure we have an open CSV file ready to write."""
    global current_writer
    if current_writer is None:
        open_new_csv()


def maybe_rollover_csv():
    """If current CSV is too large, start a new one."""
    global current_rows
    if current_rows >= ROWS_PER_FILE:
        open_new_csv()


def parse_esp32_json(line: str):
    """
    Input example:
    {"ts":"2026-02-10T23:15:42","int_10":1234,"temp_c":21.37,"mac":"AA:BB:CC:DD:EE:FF"}
    Returns (timestamp_iso, co2_ppm, temp_c, mac) or None on error.
    """
    try:
        data = json.loads(line)
    except json.JSONDecodeError:
        return None

    co2_val = data.get("int_10")
    mac_addr = data.get("mac", "")
    temp_c = data.get("temp_c")
    ts = data.get("ts")

    # co2 is required; skip if invalid
    try:
        co2_ppm = float(co2_val)
    except (TypeError, ValueError):
        return None

    # timestamp: prefer sensor ts, otherwise server time
    if ts:
        try:
            timestamp = datetime.fromisoformat(ts).isoformat()
        except ValueError:
            timestamp = datetime.now().isoformat()
    else:
        timestamp = datetime.now().isoformat()

    return timestamp, co2_ppm, temp_c, mac_addr


def open_serial():
    while True:
        try:
            ser = serial.Serial(PORT, BAUD, timeout=1)
            print(f"Opened serial port {PORT} at {BAUD} baud")
            return ser
        except Exception as e:
            print(f"Failed to open serial port {PORT}: {e}")
            time.sleep(3)


def main():
    global current_rows
    ser = open_serial()
    ensure_csv_open()
    print(f"Reading from {PORT}, logging directly to CSV")

    while True:
        try:
            line_bytes = ser.readline()
            if not line_bytes:
                continue

            try:
                decoded = line_bytes.decode("utf-8", errors="ignore").strip()
            except Exception:
                continue

            if not decoded:
                continue

            print("BT line:", decoded)

            parsed = parse_esp32_json(decoded)
            if parsed is None:
                print("Skipping line (could not parse JSON or missing CO2):", decoded)
                continue

            timestamp, co2_ppm, temp_c, mac_addr = parsed

            ensure_csv_open()
            maybe_rollover_csv()

            # Write row
            current_writer.writerow([timestamp, co2_ppm, temp_c, mac_addr])
            current_file.flush()
            current_rows += 1

        except serial.SerialException as e:
            print(f"Serial error: {e}")
            ser.close()
            time.sleep(2)
            ser = open_serial()
        except KeyboardInterrupt:
            print("Stopping bridge")
            break
        except Exception as e:
            print(f"Unexpected error in main loop: {e}")
            time.sleep(1)

    # Graceful shutdown
    if current_file is not None:
        current_file.close()
    ser.close()


if __name__ == "__main__":
    main()
