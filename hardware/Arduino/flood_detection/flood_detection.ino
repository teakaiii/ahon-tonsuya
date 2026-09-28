#include <SoftwareSerial.h>
#include <avr/pgmspace.h>
#include <EEPROM.h>
#include <string.h>

SoftwareSerial gsmSerial(7, 8);

// PINS
const int SENSOR_PIN = A0;
const int LED_GREEN  = 13;
const int LED_YELLOW = 12;
const int LED_RED    = 11;

// Calibrate RAW_DRY and RAW_WET using this sensor and the water it will measure.
const int SENSOR_RAW_DRY = 0;
const int SENSOR_RAW_WET = 600;
const float SENSOR_SPAN_CM = 4.0f;
const int SENSOR_SAMPLE_COUNT = 10;

// CONFIGURATION
const char RECIPIENT_PHONE[] PROGMEM = "+639077650549";
const size_t RECIPIENT_PHONE_SIZE = 17;
char recipientPhone[RECIPIENT_PHONE_SIZE];
const char APN[] PROGMEM = "internet";

// PUBLIC NO-AUTH ENDPOINT NG DJANGO BACKEND
const char NGROK_URL[] PROGMEM = "http://pretense-landslide-gigahertz.ngrok-free.dev/api/water-level/public-ingest/";

// THRESHOLDS
// With ADC 0-600 mapped to 0-4 cm, these are 2 cm Warning and 3 cm Danger.
const int THRESHOLD_WARNING  = 300;
const int THRESHOLD_CRITICAL = 450;

int currentAlertState = -1;
bool isGprsConnected = false;
bool hasSentWarningSMS = false;
unsigned long lastWarningSmsTime = 0;
int pendingSmsState = 0;
int lastSmsAttemptState = 0;
unsigned long lastSmsAttemptTime = 0;
bool hasAttemptedSMS = false;
const unsigned long SMS_COOLDOWN = 300000;
const unsigned long SMS_RETRY_INTERVAL = 60000;

// TIMING CONTROL
unsigned long lastHttpPostTime = 0;
int lastHttpAttemptedState = -1;
const unsigned long HTTP_POST_INTERVAL = 5000; // 5 seconds

void setup() {
  Serial.begin(9600);
  gsmSerial.begin(9600);

  pinMode(LED_GREEN, OUTPUT);
  pinMode(LED_YELLOW, OUTPUT);
  pinMode(LED_RED, OUTPUT);

  digitalWrite(LED_GREEN, HIGH);
  digitalWrite(LED_YELLOW, LOW);
  digitalWrite(LED_RED, LOW);

  Serial.println(F("========================================="));
  Serial.println(F(" AHON-FloodWatch-3 Initializing...     "));
  Serial.println(F("========================================="));

  loadRecipientPhone();
  Serial.println(F("[CONFIG] Use GET_PHONE or SET_PHONE=+639XXXXXXXXX in Serial Monitor."));

  delay(2000);
  initGSM();
}

void loop() {
  processSerialCommand();

  int waterValue = readWaterSensorRaw();
  float waterLevelCm = rawToWaterLevelCm(waterValue);

  Serial.print(F("Current Sensor ADC: "));
  Serial.print(waterValue);
  Serial.print(F(" | Water Level: "));
  Serial.print(waterLevelCm, 1);
  Serial.println(F(" cm"));

  const char *currentStatus = "Normal";
  bool sendWarningSms = false;
  bool sendCriticalSms = false;

  // ==========================================
  // 1. LED LOGIC & SMS ALERTS
  // ==========================================
  if (waterValue < THRESHOLD_WARNING) {
    digitalWrite(LED_GREEN, HIGH);
    digitalWrite(LED_YELLOW, LOW);
    digitalWrite(LED_RED, LOW);
    currentStatus = "Normal";

    if (currentAlertState != 0) {
      currentAlertState = 0;
      if (pendingSmsState == 1) {
        pendingSmsState = 0;
      }
      Serial.println(F("[STATUS] Normal Level - GREEN LED"));
    }
  }
  else if (waterValue >= THRESHOLD_WARNING && waterValue < THRESHOLD_CRITICAL) {
    digitalWrite(LED_GREEN, LOW);
    digitalWrite(LED_YELLOW, HIGH);
    digitalWrite(LED_RED, LOW);
    currentStatus = "Warning";

    if (currentAlertState != 1) {
      currentAlertState = 1;
      Serial.println(F("[STATUS] Warning Level - YELLOW LED"));
      if (!hasSentWarningSMS || millis() - lastWarningSmsTime >= SMS_COOLDOWN) {
        sendWarningSms = true;
      } else {
        Serial.println(F("[SMS] Warning alert skipped during cooldown."));
      }
    }
  }
  else if (waterValue >= THRESHOLD_CRITICAL) {
    digitalWrite(LED_GREEN, LOW);
    digitalWrite(LED_YELLOW, LOW);
    digitalWrite(LED_RED, HIGH);
    currentStatus = "Danger";

    if (currentAlertState != 2) {
      currentAlertState = 2;
      pendingSmsState = 2;
      Serial.println(F("[STATUS] CRITICAL LEVEL - RED LED! Sending Emergency SMS..."));
      sendCriticalSms = true;
    }
  }

  printSerialTelemetry(waterLevelCm, currentStatus);

  if (sendCriticalSms) {
    pendingSmsState = 2;
  } else if (sendWarningSms && pendingSmsState != 2) {
    pendingSmsState = 1;
  }

  if (pendingSmsState != 0 &&
      (!hasAttemptedSMS || pendingSmsState != lastSmsAttemptState ||
       millis() - lastSmsAttemptTime >= SMS_RETRY_INTERVAL)) {
    int attemptedState = pendingSmsState;
    lastSmsAttemptState = attemptedState;
    lastSmsAttemptTime = millis();
    hasAttemptedSMS = true;

    bool smsAccepted = attemptedState == 2
        ? sendSMS(F("EMERGENCY FLOOD ALERT: High water level detected. Evacuate immediately!"))
        : sendSMS(F("FLOOD WARNING: Water level is rising. Please stay alert and prepare for possible evacuation."));

    if (smsAccepted) {
      pendingSmsState = 0;
      if (attemptedState == 1) {
        hasSentWarningSMS = true;
        lastWarningSmsTime = millis();
      }
    }
  }

  // ==========================================
  // 2. HTTP POST TO DJANGO BACKEND
  // ==========================================
  // Upload status changes, including Danger, and refresh at the normal
  // interval. USB telemetry is emitted first so the bridge receives it before
  // the SMS and HTTP modem operations.
  if (currentAlertState != lastHttpAttemptedState ||
      millis() - lastHttpPostTime >= HTTP_POST_INTERVAL) {
    lastHttpPostTime = millis();
    lastHttpAttemptedState = currentAlertState;

    const char *gsmStatusStr = isGprsConnected ? "connected" : "disconnected";

    // FIX: reserve buffer up front to reduce heap fragmentation risk on the
    // limited RAM of an Uno/Nano when doing repeated String concatenation.
    String jsonPayload;
    jsonPayload.reserve(160);

    // FIX: removed the stray leading "{" that was producing invalid JSON
    // like {{"water_level_cm":...}  (double open-brace, single close-brace).
    jsonPayload += F("{\"water_level_cm\":");
    jsonPayload += String(waterLevelCm, 1);
    jsonPayload += F(",\"status\":\"");
    jsonPayload += currentStatus;
    jsonPayload += F("\",\"sensor_status\":\"online\",\"gsm_status\":\"");
    jsonPayload += gsmStatusStr;
    jsonPayload += F("\"}");

    bool uploadSuccess = sendHttpPost(jsonPayload);

    if (uploadSuccess) {
      Serial.println(F("[HTTP] Ingest successfully recorded in Django (201/200 OK)!"));
    } else {
      Serial.println(F("[HTTP] Upload failed or timed out. Re-checking GPRS connection..."));
      if (!isGprsConnected) {
        startGPRS();
      }
    }
  }

  delay(1000);
}

bool isValidPhoneNumber(const char *phone) {
  size_t length = strlen(phone);
  if (phone[0] != '+' || length < 9 || length >= RECIPIENT_PHONE_SIZE) {
    return false;
  }
  for (size_t index = 1; index < length; index++) {
    if (phone[index] < '0' || phone[index] > '9') {
      return false;
    }
  }
  return true;
}

void loadRecipientPhone() {
  char storedPhone[RECIPIENT_PHONE_SIZE];
  for (size_t index = 0; index < RECIPIENT_PHONE_SIZE; index++) {
    storedPhone[index] = EEPROM.read(index);
  }
  storedPhone[RECIPIENT_PHONE_SIZE - 1] = '\0';

  if (isValidPhoneNumber(storedPhone)) {
    strcpy(recipientPhone, storedPhone);
  } else {
    strncpy_P(recipientPhone, RECIPIENT_PHONE, RECIPIENT_PHONE_SIZE);
    recipientPhone[RECIPIENT_PHONE_SIZE - 1] = '\0';
  }
}

void saveRecipientPhone(const char *phone) {
  size_t length = strlen(phone);
  for (size_t index = 0; index < RECIPIENT_PHONE_SIZE; index++) {
    EEPROM.update(index, index <= length ? phone[index] : '\0');
  }
  strcpy(recipientPhone, phone);
}

void processSerialCommand() {
  static char command[32];
  static size_t commandLength = 0;

  while (Serial.available() > 0) {
    char character = Serial.read();
    if (character == '\r') {
      continue;
    }
    if (character != '\n') {
      if (commandLength < sizeof(command) - 1) {
        command[commandLength++] = character;
      } else {
        commandLength = 0;
        Serial.println(F("[CONFIG] Command too long; ignored."));
      }
      continue;
    }

    command[commandLength] = '\0';
    if (strcmp(command, "GET_PHONE") == 0) {
      Serial.print(F("[CONFIG] SMS recipient: "));
      Serial.println(recipientPhone);
    } else if (strncmp(command, "SET_PHONE=", 10) == 0) {
      const char *newPhone = command + 10;
      if (isValidPhoneNumber(newPhone)) {
        saveRecipientPhone(newPhone);
        Serial.println(F("[CONFIG] Recipient saved to EEPROM."));
      } else {
        Serial.println(F("[CONFIG] Invalid number. Use + followed by 8-15 digits, no spaces."));
      }
    } else if (commandLength > 0) {
      Serial.println(F("[CONFIG] Use GET_PHONE or SET_PHONE=+639XXXXXXXXX."));
    }
    commandLength = 0;
  }
}

int readWaterSensorRaw() {
  long total = 0;
  for (int sample = 0; sample < SENSOR_SAMPLE_COUNT; sample++) {
    total += analogRead(SENSOR_PIN);
    delay(5);
  }
  return total / SENSOR_SAMPLE_COUNT;
}

float rawToWaterLevelCm(int rawValue) {
  int rawSpan = SENSOR_RAW_WET - SENSOR_RAW_DRY;
  if (rawSpan == 0) {
    return 0.0f;
  }

  float levelCm = (float)(rawValue - SENSOR_RAW_DRY) * SENSOR_SPAN_CM / rawSpan;
  if (levelCm < 0.0f) {
    return 0.0f;
  }
  if (levelCm > SENSOR_SPAN_CM) {
    return SENSOR_SPAN_CM;
  }
  return levelCm;
}

void printSerialTelemetry(float waterLevelCm, const char *currentStatus) {
  Serial.print(F("[DEBUG] Payload: {\"water_level_cm\":"));
  Serial.print(waterLevelCm, 1);
  Serial.print(F(",\"status\":\""));
  Serial.print(currentStatus);
  Serial.print(F("\",\"sensor_status\":\"online\",\"gsm_status\":\""));
  Serial.print(isGprsConnected ? F("connected") : F("disconnected"));
  Serial.println(F("\"}"));
}

// ==========================================
// GSM & GPRS FUNCTIONS
// ==========================================
void flushGsmSerial() {
  while (gsmSerial.available()) {
    gsmSerial.read();
  }
}

void initGSM() {
  Serial.println(F("Initializing GSM Module..."));
  if (!sendATCommand(F("AT"), F("OK"), 2000)) {
    Serial.println(F("[GSM] Modem did not respond to AT."));
    return;
  }
  if (!sendATCommand(F("AT+CMGF=1"), F("OK"), 2000)) {
    Serial.println(F("[GSM] Could not set SMS text mode."));
  }

  if (!startGPRS()) {
    Serial.println(F("[GPRS] Setup failed; check SIM registration and configured APN."));
  }
  Serial.println(F("GSM System Initialization Complete."));
}

bool startGPRS() {
  sendATCommand(F("AT+HTTPTERM"), F("OK"), 1000);
  sendATCommand(F("AT+SAPBR=0,1"), F("OK"), 2000);

  if (!sendATCommand(F("AT+SAPBR=3,1,\"Contype\",\"GPRS\""), F("OK"), 3000)) {
    Serial.println(F("[GPRS] Failed to set bearer type."));
    isGprsConnected = false;
    return false;
  }
  String apnCommand;
  apnCommand.reserve(48);
  apnCommand = F("AT+SAPBR=3,1,\"APN\",\"");
  apnCommand += (const __FlashStringHelper *)APN;
  apnCommand += '"';
  if (!sendATCommand(apnCommand, F("OK"), 3000)) {
    Serial.println(F("[GPRS] Failed to set APN."));
    isGprsConnected = false;
    return false;
  }

  if (!sendATCommand(F("AT+SAPBR=3,1,\"DNS\",\"8.8.8.8\""), F("OK"), 3000)) {
    Serial.println(F("[GPRS] Primary DNS override not supported; using network DNS."));
  }
  if (!sendATCommand(F("AT+SAPBR=3,1,\"DNS2\",\"8.8.4.4\""), F("OK"), 3000)) {
    Serial.println(F("[GPRS] Secondary DNS override not supported; using network DNS."));
  }

  Serial.println(F("Opening GPRS Context..."));
  if (!sendATCommand(F("AT+SAPBR=1,1"), F("OK"), 8000)) {
    Serial.println(F("GPRS Connection Failed!"));
    isGprsConnected = false;
    return false;
  }

  Serial.println(F("GPRS Connected!"));
  isGprsConnected = true;
  return true;
}

bool sendSMS(const __FlashStringHelper *message) {
  flushGsmSerial();

  if (!sendATCommand(F("AT+CMGF=1"), F("OK"), 2000)) {
    Serial.println(F("[SMS] Could not set text mode."));
    return false;
  }

  gsmSerial.print(F("AT+CMGS=\""));
  gsmSerial.print(recipientPhone);
  gsmSerial.println(F("\""));
  String prompt = waitForResponse(F(">"), 10000);
  if (prompt.indexOf('>') == -1) {
    Serial.print(F("[SMS] No message prompt from modem: "));
    Serial.println(prompt);
    return false;
  }

  gsmSerial.print(message);
  gsmSerial.write(26); // CTRL+Z
  String result = waitForResponse(F("OK"), 30000);
  if (result.indexOf(F("+CMGS:")) != -1 && result.indexOf(F("OK")) != -1) {
    Serial.println(F(">>> SMS accepted by modem. <<<"));
    return true;
  } else {
    Serial.print(F("[SMS] Send failed: "));
    Serial.println(result);
    return false;
  }
}

bool sendHttpPost(const String &payload) {
  // FIX: force-close ANY leftover/stuck HTTP session before starting a new
  // one. If a previous cycle's cleanup HTTPTERM silently failed, the module
  // is left with a session already open, and every future AT+HTTPINIT call
  // will keep failing forever with "operation not allowed" until this is
  // done. We deliberately ignore the result here — it is expected/benign to
  // get an error if no session was actually open.
  sendATCommand(F("AT+HTTPTERM"), F("OK"), 2000);
  delay(200); // give the module a moment to fully release the HTTP context

  // FIX: verify the GPRS bearer is actually still up (has a real IP) before
  // attempting HTTP. GPRS can silently drop mid-session; isGprsConnected can
  // go stale. If the bearer is down, reopen it via startGPRS() first instead
  // of wasting a full HTTPINIT attempt that is guaranteed to fail.
  // NOTE: AT+SAPBR=2,1 ALWAYS replies with "+SAPBR:" even when the bearer is
  // closed (status 3/4) — that substring alone can't tell connected apart
  // from disconnected. We specifically look for "1,1," (cid=1, status=1
  // "connected") which only appears when the bearer genuinely has a live IP.
  flushGsmSerial();
  delay(50);
  gsmSerial.println(F("AT+SAPBR=2,1"));
  String bearerCheck = waitForResponse(F("+SAPBR:"), 3000);
  bool bearerIsUp = bearerCheck.indexOf(F("1,1,")) != -1;
  if (!bearerIsUp) {
    Serial.print(F("[HTTP] Bearer check response: "));
    Serial.println(bearerCheck);
    Serial.println(F("[HTTP] Bearer not active, reopening GPRS before HTTP attempt..."));
    if (!startGPRS()) {
      Serial.println(F("[HTTP] Could not reopen GPRS bearer; aborting this POST."));
      return false;
    }
    delay(200);
  }

  if (!sendATCommand(F("AT+HTTPINIT"), F("OK"), 5000)) {
    Serial.println(F("[HTTP] HTTPINIT failed."));
    // FIX: if HTTPINIT itself failed (e.g. still "operation not allowed"),
    // force another close attempt so the NEXT cycle at least starts clean
    // instead of compounding on top of this same stuck state.
    sendATCommand(F("AT+HTTPTERM"), F("OK"), 2000);
    return false;
  }

  String urlCommand;
  urlCommand.reserve(140);
  urlCommand = F("AT+HTTPPARA=\"URL\",\"");
  urlCommand += (const __FlashStringHelper *)NGROK_URL;
  urlCommand += '"';
  // FIX: CID and URL are the essential params — if either fails, abort.
  // CONTENT and USERDATA appear to be UNSUPPORTED tags on this particular
  // SIM900 module's firmware (they consistently fail with "operation not
  // allowed" even though HTTPINIT/CID/URL always succeed). Treat them as
  // best-effort only: try them, log if they fail, but don't block the POST
  // just because this module's firmware doesn't recognize those two tags.
  if (!sendATCommand(F("AT+HTTPPARA=\"CID\",1"), F("OK"), 3000) ||
      !sendATCommand(urlCommand, F("OK"), 3000)) {
    Serial.println(F("[HTTP] Failed to configure required request parameters (CID/URL)."));
    sendATCommand(F("AT+HTTPTERM"), F("OK"), 2000);
    return false;
  }
  if (!sendATCommand(F("AT+HTTPPARA=\"CONTENT\",\"application/json\""), F("OK"), 3000)) {
    Serial.println(F("[HTTP] Note: CONTENT param not accepted by this module (non-fatal, continuing)."));
  }
  if (!sendATCommand(F("AT+HTTPPARA=\"USERDATA\",\"ngrok-skip-browser-warning: true\""), F("OK"), 3000)) {
    Serial.println(F("[HTTP] Note: USERDATA param not accepted by this module (non-fatal, continuing)."));
  }

  String dataCmd;
  dataCmd.reserve(32);
  dataCmd = String(F("AT+HTTPDATA=")) + String(payload.length()) + F(",5000");
  if (!sendATCommand(dataCmd, F("DOWNLOAD"), 5000)) {
    Serial.println(F("[HTTP] Modem did not accept HTTPDATA."));
    sendATCommand(F("AT+HTTPTERM"), F("OK"), 1000);
    return false;
  }
  gsmSerial.print(payload);
  String dataResponse = waitForResponse(F("OK"), 10000);
  if (dataResponse.indexOf(F("OK")) == -1 || dataResponse.indexOf(F("ERROR")) != -1) {
    Serial.print(F("[HTTP] Payload was not accepted: "));
    Serial.println(dataResponse);
    sendATCommand(F("AT+HTTPTERM"), F("OK"), 1000);
    return false;
  }

  // HTTPACTION returns its status asynchronously after the immediate OK.
  gsmSerial.println(F("AT+HTTPACTION=1"));
  String actionResponse = waitForResponse(F("+HTTPACTION:"), 30000);
  sendATCommand(F("AT+HTTPTERM"), F("OK"), 2000);

  if (actionResponse.indexOf(F(",200,")) != -1 || actionResponse.indexOf(F(",201,")) != -1) {
    isGprsConnected = true;
    return true;
  } else {
    Serial.print(F("[HTTP ERROR] No successful HTTP result: "));
    Serial.println(actionResponse);
    if (actionResponse.indexOf(F("+HTTPACTION:")) == -1 ||
      actionResponse.indexOf(F(",601,")) != -1 ||
      actionResponse.indexOf(F(",602,")) != -1) {
      isGprsConnected = false;
    }
    return false;
  }
}

bool sendATCommand(const String &command, const String &expectedResponse, unsigned long timeout) {
  // FIX: drain any leftover/stale bytes still sitting in the buffer from the
  // previous exchange BEFORE sending a new command. Without this, trailing
  // bytes from the last response bleed into the next read and corrupt/garble
  // the text (e.g. "operation not ؽݕRh%I<0,1" — a mix of old + new data).
  flushGsmSerial();
  delay(50); // small settle time so the module is ready for a new command

  gsmSerial.println(command);
  String resp = waitForResponse(expectedResponse, timeout);
  bool succeeded = resp.indexOf(expectedResponse) != -1 && resp.indexOf(F("ERROR")) == -1;
  if (!succeeded) {
    Serial.print(F("[MODEM] Command failed: "));
    Serial.print(command);
    Serial.print(F(" | response: "));
    Serial.println(resp);
  }
  return succeeded;
}

String waitForResponse(const String &expectedResponse, unsigned long timeout) {
  String response;
  response.reserve(96); // FIX: cap growth tendency on repeated appends
  unsigned long startTime = millis();
  unsigned long lastByteTime = millis();
  bool foundToken = false;

  while (millis() - startTime < timeout) {
    while (gsmSerial.available()) {
      char c = gsmSerial.read();
      response += c;
      lastByteTime = millis();
    }
    if (!foundToken) {
      if (expectedResponse.length() > 0 && response.indexOf(expectedResponse) != -1) {
        foundToken = true;
      }
      if (response.indexOf(F("ERROR")) != -1) {
        foundToken = true;
      }
    }
    // FIX: once the expected token/ERROR is seen, don't return immediately —
    // keep draining for a short "settle" window (30ms of silence) so any
    // trailing bytes (extra CR/LF, etc.) are fully consumed now instead of
    // leaking into the NEXT command's response and corrupting it.
    if (foundToken && (millis() - lastByteTime > 30)) {
      break;
    }
    delay(1);
  }
  return response;
}
