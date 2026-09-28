#!/usr/bin/env python3
"""Export timestamped AHON water-level readings for analysis notebooks."""

import argparse
import csv
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DJANGO_ROOT = REPO_ROOT / "backend" / "Django"


def main():
    parser = argparse.ArgumentParser(
        description="Export water-level telemetry as a CSV for Google Colab."
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Output CSV path. Relative paths are resolved from the repository root.",
    )
    args = parser.parse_args()

    os.chdir(DJANGO_ROOT)
    sys.path.insert(0, str(DJANGO_ROOT))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "flood_detection.settings")

    import django

    django.setup()

    from apps.water_level.models import WaterLevelReading

    output = args.output if args.output.is_absolute() else REPO_ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)

    exported = 0
    in_sensor_range = 0
    with output.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=("timestamp", "water_level_cm", "status"),
        )
        writer.writeheader()
        readings = WaterLevelReading.objects.order_by("timestamp").iterator()
        for reading in readings:
            level = float(reading.water_level_cm)
            writer.writerow(
                {
                    "timestamp": reading.timestamp.isoformat(),
                    "water_level_cm": reading.water_level_cm,
                    "status": reading.status,
                }
            )
            exported += 1
            if 0 <= level <= 4:
                in_sensor_range += 1

    print(f"Exported {exported} readings to {output}")
    print(f"Readings within the current 0-4 cm sensor range: {in_sensor_range}")
    print(f"Readings outside that range for notebook review: {exported - in_sensor_range}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
