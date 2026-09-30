/*
 * AHON FloodWatch - USB Serial Firmware
 * Barangay Tonsuya, Malabon
 *
 * Hardware: Arduino Uno + analog resistive water level sensor (no GSM module).
 *
 * Streams one JSON reading per interval over the USB serial link, e.g.
 *   {"water_level_cm":23.40,"status":"Normal","sensor_status":"online","raw":164}
 *
 * scripts/serial_bridge.py reads those lines and POSTs them to the Django API,
 * which makes them show up in the admin and on the dashboard.
 *
 * Wiring
 *   Sensor S (signal) -> A0
 *   Sensor + (VCC)    -> D7   (NOT 5V - see the corrosion note below)
 *   Sensor - (GND)    -> GND
 *
 * Why D7 instead of 5V: leaving this sensor powered sits a DC voltage across
 * two exposed traces in water, which electrolyses them - the board corrodes
 * and its readings drift within days. Powering it from a digital pin lets the
 * sketch energise it only for the few milliseconds it takes to sample.
 *
 * CALIBRATION - do this before trusting any reading:
 *   1. Flash this sketch and open Serial Monitor at 9600 baud.
 *   2. With the board completely dry, note the "raw" value  -> set RAW_DRY.
 *   3. Submerge it to the top of the traces, note the value -> set RAW_WET.
 *   4. Measure that submerged trace length in cm            -> set SENSOR_SPAN_CM.
 *   5. Re-flash. Readings are linear between those two points.
 *
 * Note that raw values depend on how conductive the water is, so calibrate
 * with the water the sensor will actually sit in - tap water and flood water
 * do not read the same.
 */

// ==================== PIN CONFIGURATION ====================

#define WATER_LEVEL_SENSOR_PIN A0
#define SENSOR_POWER_PIN 7
#define LED_STATUS_PIN 13

// ==================== CALIBRATION ====================
// Replace these with the values you measured (see header).

const int   RAW_DRY        = 0;      // analogRead() when completely dry
const int   RAW_WET        = 600;    // analogRead() at full submersion
const float SENSOR_SPAN_CM = 4.0;    // physical length represented by RAW_WET

// 4.0 cm is the sensing length of the common red "Water Sensor" board - its
// exposed traces are only about 40 mm tall. It cannot read deeper than that,
// whatever the thresholds below say. See docs/HARDWARE_SETUP.md.

// ==================== FLOOD THRESHOLDS (cm) ====================
// Keep these in sync with the Django settings of the same name.

const float ALERT_THRESHOLD   = 2.0;
const float WARNING_THRESHOLD = 2.0;
const float DANGER_THRESHOLD  = 3.0;

// ==================== TIMING ====================

const unsigned long READING_INTERVAL = 5000;  // ms between readings
const int           SAMPLE_COUNT     = 10;    // samples averaged per reading

unsigned long lastReadingTime = 0;

// ==================== SETUP ====================

void setup() {
  Serial.begin(9600);
  pinMode(WATER_LEVEL_SENSOR_PIN, INPUT);
  pinMode(SENSOR_POWER_PIN, OUTPUT);
  pinMode(LED_STATUS_PIN, OUTPUT);

  // Keep the sensor unpowered between readings.
  digitalWrite(SENSOR_POWER_PIN, LOW);

  // Give the bridge a moment to open the port before the first reading.
  delay(2000);
}

// ==================== MAIN LOOP ====================

void loop() {
  unsigned long now = millis();

  // millis() overflows after ~49 days; the subtraction handles the wrap.
  if (now - lastReadingTime >= READING_INTERVAL) {
    lastReadingTime = now;

    int   raw   = readRawAveraged();
    float level = rawToCentimetres(raw);
    publishReading(level, raw);
    updateStatusLED(level);
  }
}

// ==================== SENSOR ====================

int readRawAveraged() {
  // Power up, sample, power down - see the corrosion note in the header.
  digitalWrite(SENSOR_POWER_PIN, HIGH);
  delay(10);  // let the divider settle before the first sample

  long total = 0;
  for (int i = 0; i < SAMPLE_COUNT; i++) {
    total += analogRead(WATER_LEVEL_SENSOR_PIN);
    delay(5);
  }

  digitalWrite(SENSOR_POWER_PIN, LOW);
  return (int)(total / SAMPLE_COUNT);
}

float rawToCentimetres(int raw) {
  int span = RAW_WET - RAW_DRY;
  if (span == 0) {
    return 0.0;  // guard against a miscalibrated build
  }

  float level = (float)(raw - RAW_DRY) * SENSOR_SPAN_CM / (float)span;

  if (level < 0.0) {
    level = 0.0;
  }
  if (level > SENSOR_SPAN_CM) {
    level = SENSOR_SPAN_CM;
  }
  return level;
}

String determineFloodStatus(float level) {
  if (level >= DANGER_THRESHOLD) {
    return "Danger";
  } else if (level >= WARNING_THRESHOLD) {
    return "Warning";
  } else if (level >= ALERT_THRESHOLD) {
    return "Alert";
  }
  return "Normal";
}

// ==================== OUTPUT ====================

void publishReading(float level, int raw) {
  // Built by hand rather than with ArduinoJson - one flat object, no dependency.
  Serial.print(F("{\"water_level_cm\":"));
  Serial.print(level, 2);
  Serial.print(F(",\"status\":\""));
  Serial.print(determineFloodStatus(level));
  Serial.print(F("\",\"sensor_status\":\""));
  Serial.print(isSensorPlausible(raw) ? F("online") : F("error"));
  Serial.print(F("\",\"raw\":"));
  Serial.print(raw);
  Serial.println(F("}"));
}

bool isSensorPlausible(int raw) {
  // A dry board legitimately reads ~0, so only a pinned-high value indicates a
  // fault (signal shorted to VCC). A disconnected sensor also reads near 0 and
  // is genuinely indistinguishable from "dry" on this hardware.
  return raw <= RAW_WET;
}

void updateStatusLED(float level) {
  digitalWrite(LED_STATUS_PIN, level >= ALERT_THRESHOLD ? HIGH : LOW);
}
