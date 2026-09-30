import json
import unittest
from types import SimpleNamespace

from scripts.serial_bridge import BridgeConfig, parse_line, raw_to_cm


class SerialBridgeCalibrationTests(unittest.TestCase):
    def setUp(self):
        self.config = BridgeConfig(SimpleNamespace(
            raw_dry=0,
            raw_full=600,
            span_cm=4.0,
            gsm_status="disconnected",
        ))

    def test_raw_conversion_clamps_to_calibrated_span(self):
        self.assertEqual(raw_to_cm(900, 0, 600, 4.0), 4.0)

    def test_json_reading_above_calibrated_span_is_ignored(self):
        line = json.dumps({"water_level_cm": 4.26, "status": "Danger"})

        self.assertIsNone(parse_line(line, self.config))

    def test_reading_at_calibrated_limit_is_preserved(self):
        line = json.dumps({"water_level_cm": 4.0, "status": "Danger"})

        reading = parse_line(line, self.config)

        self.assertEqual(reading["water_level_cm"], 4.0)
        self.assertEqual(reading["status"], "Danger")

    def test_raw_reading_above_calibrated_sensor_is_ignored(self):
        self.assertIsNone(parse_line("Current Sensor Value: 601", self.config))


if __name__ == "__main__":
    unittest.main()