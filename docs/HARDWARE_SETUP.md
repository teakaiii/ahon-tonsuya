# Hardware Setup Guide

## Table of Contents

1. [Hardware Components](#hardware-components)
2. [Wiring Diagram](#wiring-diagram)
3. [Assembly Instructions](#assembly-instructions)
4. [Firmware Installation](#firmware-installation)
5. [Configuration](#configuration)
6. [Testing](#testing)
7. [Troubleshooting](#troubleshooting)
8. [Maintenance](#maintenance)

## About AHON FloodWatch Hardware

This guide covers the hardware setup for AHON FloodWatch, the flood detection and monitoring system for Barangay Tonsuya, Malabon.

## Hardware Components

### Required Components

1. **Arduino Uno** - Microcontroller
2. **Water Level Sensor** - Analog water level sensor
3. **SIM800L GSM/GPRS Module** - For cellular communication
4. **SIM Card** - With active data plan
5. **Solar Panel** - 5V 10W (for power)
6. **Rechargeable Battery** - 12V 10Ah Li-ion or similar
7. **Solar Charge Controller** - PWM or MPPT
8. **Breadboard and Jumper Wires** - For connections
9. **LED (Optional)** - Status indicator
10. **Buzzer (Optional)** - Audio alert

### Optional Components

1. **Waterproof Enclosure** - For outdoor installation
2. **Mounting Hardware** - For sensor placement
3. **Cable Glands** - For waterproof cable entry
4. **Voltage Regulator** - If using different power source
5. **SD Card Module** - For local data logging

### Component Specifications

#### Arduino Uno
- Microcontroller: ATmega328P
- Operating Voltage: 5V
- Digital I/O Pins: 14
- Analog Input Pins: 6
- Flash Memory: 32 KB
- SRAM: 2 KB

#### Water Level Sensor
- Type: Analog resistive sensor
- Operating Voltage: 3.3V - 5V
- Detection Range: 0-100 cm (adjustable)
- Output: Analog voltage 0-5V
- Operating Temperature: -20°C to 85°C

#### SIM800L GSM Module
- Operating Voltage: 3.4V - 4.4V
- Frequency: Quad-band (850/900/1800/1900 MHz)
- Data: GPRS Class 10
- SMS: Support
- Operating Temperature: -40°C to 85°C

#### Solar Panel
- Power: 10W
- Voltage: 18V (open circuit)
- Current: 0.56A (short circuit)
- Type: Monocrystalline

#### Battery
- Type: Li-ion or LiFePO4
- Voltage: 12V
- Capacity: 10Ah
- Protection: Built-in BMS

## Wiring Diagram

### Arduino to Water Level Sensor

```
Water Level Sensor    Arduino Uno
-------------------   ------------
VCC                  5V
GND                  GND
Signal (Analog)      A0
```

### Arduino to SIM800L

```
SIM800L              Arduino Uno
------              ------------
VCC                 5V (via voltage regulator)
GND                 GND
TX                  D7 (RX)
RX                  D8 (TX)
```

### Power System

```
Solar Panel → Solar Charge Controller → Battery → Voltage Regulator → Arduino + SIM800L
```

### Optional Components

```
LED → D13 (with 220Ω resistor to GND)
Buzzer → D9 (with 100Ω resistor to GND)
```

## Assembly Instructions

### Step 1: Prepare the Workspace

1. Choose a clean, well-lit workspace
2. Gather all components and tools
3. Have the wiring diagram ready for reference
4. Ensure you have proper safety equipment (anti-static wrist strap)

### Step 2: Install Arduino IDE

1. Download Arduino IDE from [arduino.cc](https://www.arduino.cc/en/software)
2. Install the IDE on your computer
3. Install the necessary drivers:
   - CH340 driver (if using clone Arduino)
   - USB Serial drivers

### Step 3: Connect Water Level Sensor

1. Connect the water level sensor VCC to Arduino 5V
2. Connect GND to Arduino GND
3. Connect the signal pin to Arduino A0
4. Secure the sensor in its mounting location
5. Route the cable away from water sources

### Step 4: Connect SIM800L Module

**Important**: SIM800L requires 3.7V - 4.2V. Do not connect directly to Arduino 5V.

1. Use a voltage regulator or buck converter to step down 5V to 4V
2. Connect regulated power to SIM800L VCC
3. Connect GND to common ground
4. Connect SIM800L TX to Arduino D7 (SoftwareSerial RX)
5. Connect SIM800L RX to Arduino D8 (SoftwareSerial TX)
6. Insert SIM card into the module
7. Ensure SIM card has active data plan

### Step 5: Connect Power System

1. Connect solar panel to solar charge controller
2. Connect battery to solar charge controller
3. Connect battery output to voltage regulator
4. Connect voltage regulator output to Arduino VIN
5. Connect regulated power to SIM800L
6. Add a power switch for easy on/off control

### Step 6: Install Optional Components

1. Connect LED to D13 with 220Ω resistor to GND
2. Connect buzzer to D9 with 100Ω resistor to GND
3. Add any additional sensors or modules as needed

### Step 7: Enclosure Assembly

1. Drill holes in enclosure for:
   - Power cable entry
   - Sensor cable entry
   - Antenna cable (for SIM800L)
   - USB programming cable access
2. Install cable glands for waterproofing
3. Mount Arduino and components inside enclosure
4. Ensure proper ventilation
5. Seal enclosure properly

### Step 8: Sensor Installation

1. Choose appropriate location for water level sensor:
   - Near water source to be monitored
   - Protected from debris
   - Accessible for maintenance
2. Mount sensor securely
3. Calibrate sensor based on installation height
4. Test sensor readings

## Firmware Installation

### Step 1: Download Firmware

1. Navigate to `hardware/Arduino/flood_detection.ino`
2. Open the file in Arduino IDE

### Step 2: Configure Firmware

Edit the configuration section at the top of the file:

```cpp
// Pin Definitions
#define WATER_LEVEL_SENSOR_PIN A0
#define SIM800L_TX_PIN 7
#define SIM800L_RX_PIN 8
#define LED_STATUS_PIN 13
#define BUZZER_PIN 9

// Current 4 cm sensor calibration: ADC 0-600 maps to 0-4 cm.
// These boundaries produce the three states Normal, Warning, and Danger.
const int THRESHOLD_WARNING = 300;  // 2 cm: Warning begins
const int THRESHOLD_CRITICAL = 450; // 3 cm: Critical/Danger begins

// Timing Configuration
#define READING_INTERVAL 30000      // 30 seconds
#define UPLOAD_INTERVAL 30000      // 30 seconds
#define SMS_COOLDOWN 300000        // 5 minutes
#define RETRY_DELAY 5000           // 5 seconds
#define MAX_RETRIES 3              // Maximum retry attempts

// Firebase Configuration
#define FIREBASE_HOST "your-project-id.firebaseio.com"
#define FIREBASE_AUTH "your-firebase-auth-token"
#define FIREBASE_PATH "/water_level"

// SMS Configuration
#define ADMIN_NUMBER "+639123456789"
```

### Step 3: Install Required Libraries

In Arduino IDE, install these libraries via Library Manager:
- ArduinoJson by Benoit Blanchon
- SoftwareSerial (built-in)

### Step 4: Select Board and Port

1. Tools → Board → Arduino Uno
2. Tools → Port → Select your Arduino's COM port

### Step 5: Upload Firmware

1. Click the Upload button (→)
2. Wait for upload to complete
3. Check for "Done uploading" message

### Step 6: Verify Installation

1. Open Serial Monitor (Ctrl+Shift+M)
2. Set baud rate to 9600
3. Power on the Arduino
4. Check for initialization messages

## Configuration

### Firebase Setup

1. Create a Firebase project at [console.firebase.google.com](https://console.firebase.google.com)
2. Enable Realtime Database
3. Generate service account key
4. Copy project ID and auth token
5. Update firmware configuration

### SIM Card Configuration

1. Ensure SIM card has active data plan
2. Test SIM card in a phone first
3. Configure APN settings in firmware:
   ```cpp
   sendATCommand("AT+SAPBR=3,1,\"APN\",\"internet.globe.com.ph\"", "OK", 2000);
   ```
4. Replace with your network provider's APN

### Sensor Calibration

1. With the sensor dry, record its averaged ADC value as `SENSOR_RAW_DRY` (GSM sketch) or `RAW_DRY` (USB sketch).
2. Submerge the active traces to their measured full span and record the ADC value as `SENSOR_RAW_WET` or `RAW_WET`.
3. Set `SENSOR_SPAN_CM` to the measured physical span in centimetres. Keep the same dry value, wet value, and span in `scripts/serial_bridge.py` (`--raw-dry`, `--raw-full`, and `--span-cm`).
4. Reflash the Arduino and verify several dry, midpoint, and full-span readings against a ruler before connecting operational alerts.
5. Readings outside the calibrated ADC or centimetre range are marked faulty or rejected; the dashboard excludes them from the current value and trend chart, and flags an older fallback reading as stale.

Do not map the 10-bit ADC range to an assumed 0-100 cm. Conductivity varies with the water, and this sensor only measures its calibrated active span. The default configuration is 0-600 ADC for 0-4 cm and must be replaced with site measurements if it differs.

### Threshold Configuration

Set appropriate thresholds based on your location:
- **Normal Threshold**: Safe water level
- **Alert Threshold**: Level to start monitoring closely
- **Warning Threshold**: Level to prepare for evacuation
- **Danger Threshold**: Critical level requiring immediate action

## Testing

### Hardware Testing

#### Water Level Sensor Test

1. Place sensor at different water levels
2. Monitor Serial Monitor for readings
3. Verify readings are accurate
4. Check for consistent readings

#### SIM800L Test

1. Open Serial Monitor
2. Check for "SIM800L is responding" message
3. Verify SIM card status
4. Check signal strength
5. Test GPRS connection

#### Power System Test

1. Disconnect main power
2. Verify system runs on battery
3. Monitor battery voltage
4. Test solar charging

### Integration Testing

#### Firebase Upload Test

1. Check Firebase console
2. Verify data is being uploaded
3. Check data format
4. Verify timestamp accuracy

#### SMS Alert Test

1. Manually trigger danger condition
2. Verify SMS is sent
3. Check SMS content
4. Verify recipient receives message

#### Full System Test

1. Run system for 24 hours
2. Monitor all components
3. Check data consistency
4. Verify battery performance
5. Test all alert levels

## Troubleshooting

### Common Issues

#### Arduino Not Detected

**Symptoms**: Port not showing in Arduino IDE

**Solutions**:
- Check USB cable connection
- Install proper drivers
- Try different USB port
- Test with different computer
- Check Arduino power LED

#### Sensor Not Reading

**Symptoms**: Water level readings are 0 or inconsistent

**Solutions**:
- Check sensor connections
- Verify sensor is powered
- Test sensor with multimeter
- Check analog pin configuration
- Calibrate sensor

#### SIM800L Not Responding

**Symptoms**: "SIM800L not responding" message

**Solutions**:
- Check power supply (must be 3.7V - 4.2V)
- Verify SIM card is inserted properly
- Check TX/RX connections
- Test SIM card in phone
- Verify antenna is connected

#### No GPRS Connection

**Symptoms**: "Failed to attach to GPRS" message

**Solutions**:
- Check SIM card has data plan
- Verify APN settings
- Check signal strength
- Test with different SIM card
- Contact network provider

#### Firebase Upload Fails

**Symptoms**: Data not appearing in Firebase

**Solutions**:
- Verify Firebase credentials
- Check internet connection
- Verify GPRS is connected
- Check Firebase project settings
- Review error messages in Serial Monitor

#### SMS Not Sending

**Symptoms**: SMS alerts not received

**Solutions**:
- Verify recipient number format (+63XXXXXXXXXX)
- Check SMS balance
- Verify GSM module is working
- Check rate limiting
- Review error messages

#### Battery Draining Fast

**Symptoms**: Battery doesn't last through the night

**Solutions**:
- Check solar panel output
- Verify charge controller is working
- Reduce reading/upload intervals
- Check for power leaks
- Consider larger battery

### Debug Mode

Enable debug mode in firmware by uncommenting:
```cpp
#define DEBUG_MODE
```

This will print detailed information to Serial Monitor.

## Maintenance

### Regular Maintenance

#### Daily
- Check system status via dashboard
- Monitor battery level
- Verify data is being uploaded

#### Weekly
- Inspect physical connections
- Check sensor cleanliness
- Verify SMS functionality
- Review error logs

#### Monthly
- Clean solar panel
- Check battery health
- Update firmware if needed
- Calibrate sensor
- Backup configuration

#### Quarterly
- Test full system
- Replace SIM card if needed
- Check enclosure seals
- Review and update thresholds
- Performance analysis

### Sensor Maintenance

1. **Clean sensor regularly** to remove debris
2. **Check for corrosion** on connections
3. **Calibrate periodically** for accuracy
4. **Replace if readings become inconsistent**

### Battery Maintenance

1. **Monitor battery voltage** regularly
2. **Check for swelling or damage**
3. **Test battery capacity** periodically
4. **Replace every 2-3 years** depending on usage

### Solar Panel Maintenance

1. **Clean panel surface** regularly
2. **Check for damage or cracks**
3. **Verify connections are secure**
4. **Test output voltage** periodically

### Winter/Off-Season Storage

If system won't be used for extended period:

1. **Disconnect solar panel**
2. **Charge battery to 100%**
3. **Store battery in cool, dry place**
4. **Remove SIM card** if not needed
5. **Protect from moisture**

## Safety Precautions

### Electrical Safety

- Always disconnect power before working on wiring
- Use proper voltage regulation
- Avoid water contact with electronics
- Use waterproof connections

### Installation Safety

- Install in safe, accessible location
- Secure all components properly
- Use appropriate mounting hardware
- Consider weather protection

### Battery Safety

- Use proper battery type and rating
- Include battery protection circuit
- Store batteries properly
- Dispose of old batteries properly

### General Safety

- Follow local regulations
- Obtain necessary permits
- Work with qualified personnel if unsure
- Keep emergency contact information

## Appendix

### Pin Reference

| Arduino Pin | Connected To | Function |
|-------------|---------------|----------|
| A0 | Water Level Sensor | Analog Input |
| D7 | SIM800L TX | SoftwareSerial RX |
| D8 | SIM800L RX | SoftwareSerial TX |
| D9 | Buzzer (Optional) | Digital Output |
| D13 | LED (Optional) | Digital Output |
| 5V | Sensor, Regulator Input | Power |
| GND | All Components | Common Ground |
| VIN | Voltage Regulator Output | Power Input |

### APN Settings by Provider

| Provider | APN |
|----------|-----|
| Globe | internet.globe.com.ph |
| Smart | internet |
| Sun Cellular | wap |
| TNT | internet |

### Contact Information

- **Technical Support**: [Contact details]
- **Hardware Vendor**: [Contact details]
- **Network Provider**: [Contact details]

### Version History

- **v1.0.0** (2026-07-13): Initial hardware setup guide
