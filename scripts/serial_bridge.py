#!/usr/bin/env python3
"""
AHON FloodWatch - Arduino serial bridge.

Reads JSON reading lines from the Arduino over USB serial and POSTs them to the
Django API, so they appear in the Django admin and on the React dashboard.

    Arduino --USB serial--> serial_bridge.py --HTTP--> /api/water-level/readings/create/

The Arduino has no clock, so this script stamps each reading with the host time.

Usage:
    python scripts/serial_bridge.py --username admin --password admin123
    python scripts/serial_bridge.py --port /dev/cu.usbmodem14101
    python scripts/serial_bridge.py --simulate          # no hardware needed

Requires: pyserial, requests
"""

import argparse
import glob
import json
import logging
import math
import os
import random
import re
import sys
import time
from datetime import datetime, timezone

import requests

logger = logging.getLogger("serial_bridge")

# Serial devices an Arduino typically shows up as on macOS and Linux.
PORT_GLOBS = [
    "/dev/cu.usbmodem*",
    "/dev/cu.usbserial*",
    "/dev/cu.wchusbserial*",
    "/dev/ttyACM*",
    "/dev/ttyUSB*",
]

VALID_STATUSES = {"Normal", "Alert", "Warning", "Danger"}
VALID_SENSOR_STATUSES = {"online", "offline", "error"}
VALID_GSM_STATUSES = {"connected", "disconnected", "error"}


class BridgeConfig:
    """Calibration and reporting options shared by the line parsers."""

    def __init__(self, args):
        self.raw_dry = args.raw_dry
        self.raw_full = args.raw_full
        self.span_cm = args.span_cm
        self._gsm_mode = args.gsm_status
        self._gsm_seen = False

    @property
    def gsm_status(self):
        if self._gsm_mode != "auto":
            return self._gsm_mode
        return "connected" if self._gsm_seen else "disconnected"

    def note_line(self, line):
        """Watch for the sketch's GSM banner when running in auto mode.

        Caveat: sketch_sep12a.ino prints "GSM Module Ready." unconditionally
        after issuing its AT commands - it never reads the module's reply. So
        this reflects what the firmware claims, not a verified module.
        """
        if GSM_READY_RE.search(line):
            self._gsm_seen = True

    def resolve_gsm_status(self, payload_status):
        """Prefer an explicit CLI override, otherwise use device status or detection."""
        if self._gsm_mode != "auto":
            return self._gsm_mode
        if payload_status in VALID_GSM_STATUSES:
            return payload_status
        return self.gsm_status


class APIClient:
    """Thin client that keeps a JWT alive and posts readings."""

    def __init__(self, base_url, username, password):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.access = None
        self.refresh = None

    def login(self):
        resp = requests.post(
            f"{self.base_url}/api/auth/login/",
            json={"username": self.username, "password": self.password},
            timeout=10,
        )
        if resp.status_code != 200:
            raise RuntimeError(
                f"Login failed ({resp.status_code}). Check --username/--password. {resp.text[:200]}"
            )
        payload = resp.json()
        self.access = payload["access"]
        self.refresh = payload.get("refresh")
        logger.info("Authenticated with %s as %s", self.base_url, self.username)

    def _refresh_access(self):
        """Re-authenticate.

        The backend exposes no /api/auth/token/refresh/ route, so the refresh
        token is unusable here and a fresh login is the only option.
        """
        self.login()

    def post_reading(self, reading):
        """POST one reading, retrying once after re-auth. Returns True on success."""
        url = f"{self.base_url}/api/water-level/readings/create/"

        for attempt in (1, 2):
            if not self.access:
                self.login()

            try:
                resp = requests.post(
                    url,
                    json=reading,
                    headers={"Authorization": f"Bearer {self.access}"},
                    timeout=10,
                )
            except requests.RequestException as exc:
                logger.warning("POST failed: %s", exc)
                return False

            if resp.status_code in (200, 201):
                return True

            if resp.status_code == 401 and attempt == 1:
                logger.info("Token rejected, re-authenticating")
                self._refresh_access()
                continue

            logger.error("API rejected reading (%s): %s", resp.status_code, resp.text[:300])
            return False

        return False


def autodetect_port():
    """Return the single obvious serial port, or None."""
    if sys.platform == "win32":
        from serial.tools import list_ports

        ports = list(list_ports.comports())
        usb_serial_markers = ("arduino", "usb serial", "usb-serial", "ch340", "cp210", "ftdi")
        candidates = [
            port for port in ports
            if any(
                marker in f"{port.description} {port.manufacturer or ''} {port.hwid}".lower()
                for marker in usb_serial_markers
            )
        ]
        if len(candidates) == 1:
            return candidates[0].device
        if candidates:
            logger.warning(
                "Multiple USB serial ports found: %s. Pass --port explicitly.",
                ", ".join(port.device for port in candidates),
            )
            return None
        if ports:
            logger.warning(
                "Serial ports found but no recognizable USB serial device: %s. Pass --port explicitly.",
                ", ".join(f"{port.device} ({port.description})" for port in ports),
            )
            return None

    found = []
    for pattern in PORT_GLOBS:
        found.extend(glob.glob(pattern))

    # Ignore the Bluetooth pseudo-ports macOS always exposes.
    found = [p for p in found if "Bluetooth" not in p]

    if not found:
        return None
    if len(found) > 1:
        logger.warning("Multiple serial ports found: %s", ", ".join(found))
    return sorted(found)[0]


# sketch_sep12a.ino prints "Current Sensor Value: 486" rather than JSON.
RAW_LINE_RE = re.compile(r"Current Sensor Value:\s*(\d+)")
GSM_READY_RE = re.compile(r"GSM Module Ready")


def raw_to_cm(raw, raw_dry, raw_full, span_cm):
    """Linear map from the analog reading to centimetres of water."""
    span = raw_full - raw_dry
    if span <= 0:
        return 0.0
    level = (raw - raw_dry) * span_cm / span
    return round(max(0.0, min(999.99, level)), 2)


def parse_line(line, cfg):
    """Turn one serial line into a reading dict, or None if it isn't one."""
    line = line.strip()
    if not line:
        return None

    if line.startswith("[DEBUG] Payload: "):
        line = line.partition(": ")[2]

    cfg.note_line(line)

    # The plain-text sketch reports a raw ADC value; convert it here.
    match = RAW_LINE_RE.search(line)
    if match:
        level = raw_to_cm(int(match.group(1)), cfg.raw_dry, cfg.raw_full, cfg.span_cm)
        return build_reading(level, derive_status(level), "online", cfg)

    if not line.startswith("{"):
        # Status banners and boot noise are expected; ignore them quietly.
        return None

    try:
        data = json.loads(line)
    except json.JSONDecodeError:
        logger.debug("Ignoring unparsable line: %s", line[:120])
        return None

    if "water_level_cm" not in data:
        return None

    try:
        level = round(float(data["water_level_cm"]), 2)
    except (TypeError, ValueError):
        logger.warning("Ignoring non-numeric water_level_cm: %r", data.get("water_level_cm"))
        return None

    if math.isnan(level) or math.isinf(level) or not 0 <= level <= 999.99:
        logger.warning("Ignoring out-of-range water level: %s", level)
        return None

    status = data.get("status")
    if status not in VALID_STATUSES:
        # The API requires status, so derive it rather than letting the POST 400.
        status = derive_status(level)

    sensor_status = data.get("sensor_status")
    if sensor_status not in VALID_SENSOR_STATUSES:
        sensor_status = "online"

    return build_reading(level, status, sensor_status, cfg, data.get("gsm_status"))


def build_reading(level, status, sensor_status, cfg, gsm_status=None):
    return {
        "water_level_cm": level,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sensor_status": sensor_status,
        "gsm_status": cfg.resolve_gsm_status(gsm_status),
    }


def should_post_reading(reading_status, last_post, last_status, min_interval, now):
    """Post at the normal interval, or immediately when telemetry status changes."""
    return reading_status != last_status or now - last_post >= min_interval


# Matches the Arduino ADC thresholds converted to centimetres for the 4 cm strip.
def derive_status(level, warning=2.0, danger=3.0):
    if level >= danger:
        return "Danger"
    if level >= warning:
        return "Warning"
    return "Normal"


def simulated_lines(interval):
    """Yield Arduino-shaped JSON lines without any hardware attached."""
    level = 1.0
    while True:
        # Kept within the ~4 cm the real strip can actually reach.
        level = max(0.0, min(4.2, level + random.uniform(-0.4, 0.45)))
        yield json.dumps(
            {
                "water_level_cm": round(level, 2),
                "status": derive_status(level),
                "sensor_status": "online",
                "raw": int(level * 7),
            }
        )
        time.sleep(interval)


def serial_lines(port, baud, reconnect_delay):
    """Yield lines from the serial port, reconnecting if the cable drops."""
    import serial  # imported here so --simulate works without pyserial

    while True:
        try:
            logger.info("Opening %s at %d baud", port, baud)
            with serial.Serial(port, baud, timeout=2) as conn:
                # Opening the port resets an Uno; wait out the bootloader.
                time.sleep(2)
                conn.reset_input_buffer()
                logger.info("Listening for readings (Ctrl+C to stop)")

                while True:
                    raw = conn.readline()
                    if not raw:
                        continue  # read timeout, just poll again
                    yield raw.decode("utf-8", errors="replace")

        except serial.SerialException as exc:
            logger.error("Serial error: %s", exc)
            logger.info("Reconnecting in %ss", reconnect_delay)
            time.sleep(reconnect_delay)


def main():
    parser = argparse.ArgumentParser(
        description="Bridge Arduino water level readings into the AHON FloodWatch API.",
    )
    parser.add_argument("--port", help="Serial port (auto-detected if omitted)")
    parser.add_argument("--baud", type=int, default=9600, help="Baud rate (default: 9600)")
    parser.add_argument(
        "--api",
        default=os.environ.get("FLOODWATCH_API", "http://localhost:8000"),
        help="Django base URL (default: http://localhost:8000)",
    )
    parser.add_argument("--username", default=os.environ.get("FLOODWATCH_USER", "admin"))
    parser.add_argument("--password", default=os.environ.get("FLOODWATCH_PASSWORD"))
    parser.add_argument(
        "--min-interval",
        type=float,
        default=10.0,
        help="Minimum seconds between stored readings (default: 10)",
    )
    parser.add_argument(
        "--reconnect-delay", type=float, default=5.0, help="Seconds to wait before reopening the port"
    )
    parser.add_argument(
        "--raw-dry", type=int, default=0, help="analogRead value with the sensor dry (default: 0)"
    )
    parser.add_argument(
        "--raw-full", type=int, default=600,
        help="analogRead value at full submersion (default: 600)",
    )
    parser.add_argument(
        "--span-cm", type=float, default=4.0,
        help="Centimetres of water represented by --raw-full (default: 4.0)",
    )
    parser.add_argument(
        "--gsm-status", choices=("auto", "connected", "disconnected"), default="auto",
        help="GSM state override; 'auto' trusts device telemetry then the sketch banner (default: auto)",
    )
    parser.add_argument("--simulate", action="store_true", help="Generate fake readings, no hardware")
    parser.add_argument("--once", action="store_true", help="Post a single reading and exit")
    parser.add_argument("--verbose", action="store_true", help="Debug logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
    )

    if not args.password:
        parser.error("--password is required (or set FLOODWATCH_PASSWORD)")

    cfg = BridgeConfig(args)
    client = APIClient(args.api, args.username, args.password)
    try:
        client.login()
    except (RuntimeError, requests.RequestException) as exc:
        logger.error("%s", exc)
        logger.error("Is the backend running?  cd backend/Django && .venv/bin/python manage.py runserver 8000")
        return 1

    if args.simulate:
        source = simulated_lines(min(args.min_interval, 5.0))
    else:
        port = args.port or autodetect_port()
        if not port:
            logger.error("No serial port found. Plug in the Arduino, or pass --port explicitly.")
            logger.error("Ports are usually /dev/cu.usbmodem* on macOS, /dev/ttyACM* on Linux.")
            return 1
        source = serial_lines(port, args.baud, args.reconnect_delay)

    posted = 0
    skipped = 0
    last_post = 0.0
    last_status = None

    try:
        for line in source:
            reading = parse_line(line, cfg)
            if reading is None:
                continue

            # Throttle: the sketch reads faster than the DB needs rows.
            now = time.monotonic()
            if not args.once and not should_post_reading(
                reading["status"], last_post, last_status, args.min_interval, now
            ):
                skipped += 1
                continue

            if client.post_reading(reading):
                last_post = now
                last_status = reading["status"]
                posted += 1
                logger.info(
                    "Stored %.2f cm (%s)  [posted=%d skipped=%d]",
                    reading["water_level_cm"],
                    reading["status"],
                    posted,
                    skipped,
                )
                if args.once:
                    return 0

    except KeyboardInterrupt:
        logger.info("Stopped. %d readings posted, %d throttled.", posted, skipped)

    return 0


if __name__ == "__main__":
    sys.exit(main())
