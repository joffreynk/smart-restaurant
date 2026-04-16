# Waiter Robot Upload Guide

## Option 1: Using PlatformIO (Recommended)

### Install PlatformIO
```bash
# Install via pip
pip install platformio

# Or download from https://platformio.org/platformio-ide
```

### Upload Steps
```bash
cd waiter

# Build the project
pio run

# Upload to ESP32
pio run --target upload

# Or upload with monitor
pio run --target upload && pio device monitor
```

---

## Option 2: Using Arduino IDE

### Setup Arduino IDE for ESP32

1. **Install Arduino IDE** from https://www.arduino.cc/en/software

2. **Add ESP32 Board**:
   - Open Arduino IDE
   - Go to File → Preferences
   - Add to "Additional Board Manager URLs":
     ```
     https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
     ```
   - Go to Tools → Board → Board Manager
   - Search "ESP32" and install

3. **Configure Board**:
   - Board: "ESP32 Dev Module"
   - Upload Speed: "115200"
   - Flash Frequency: "80MHz"
   - Partition Scheme: "Default"

### Upload Steps

1. Create a new sketch and copy the contents from `src/main.cpp`

2. Create these library files in your sketch folder:
   - `motor.cpp` - Motor control code
   - `sensor.cpp` - Ultrasonic and battery sensors
   - `wifi.cpp` - WiFi and WebSocket communication
   - `config.h` - Configuration constants

3. Upload: Click Upload button (Ctrl+U)

---

## Option 3: Using esptool (Command Line)

### Install esptool
```bash
pip install esptool
```

### Upload Binary
```bash
# First compile with PlatformIO to get the binary
pio run

# Then flash using esptool
esptool.py --chip esp32 --port /dev/ttyUSB0 erase_flash
esptool.py --chip esp32 --port /dev/ttyUSB0 write_flash 0x1000 .pio/build/esp32-wroom-32/bootloader.bin 0x8000 .pio/build/esp32-wroom-32/partitions.bin 0x10000 .pio/build/esp32-wroom-32/firmware.bin
```

---

## Wiring Diagram

```
ESP32 GPIO Connections:

Motor Left:
  GPIO12 → Motor IN1
  GPIO14 → Motor IN2
  GPIO13 → Motor PWM (ENA)

Motor Right:
  GPIO26 → Motor IN1
  GPIO27 → Motor IN2
  GPIO25 → Motor PWM (ENA)

Ultrasonic Sensors:
  Front:  GPIO5 (TRIG), GPIO18 (ECHO)
  Left:   GPIO16 (TRIG), GPIO17 (ECHO)
  Right:  GPIO19 (TRIG), GPIO21 (ECHO)

Battery:
  GPIO34 → ADC (Voltage divider)

Status LED:
  GPIO2 → LED + Resistor → GND
```

---

## Configuration

Edit `include/config.h` before uploading:

```cpp
// WiFi credentials
#define WIFI_SSID "YourRestaurantWiFi"
#define WIFI_PASSWORD "YourPassword"

// Master controller IP
#define MASTER_IP "192.168.1.100"
#define MASTER_PORT 8765

// Robot ID (must match database)
#define ROBOT_UNIQUE_ID "ROBOT-001"
#define ROBOT_NAME "Waiter Bot Alpha"
```

---

## Troubleshooting

### Upload Issues
1. **Driver not found**: Install CH340/CP2102 USB driver
2. **Port not found**: Check USB connection, try different port
3. **Boot mode**: Hold BOOT button during upload

### Runtime Issues
1. **WiFi connection failed**: Check SSID/password, ensure same network as master
2. **WebSocket not connecting**: Verify master IP and port
3. **Motors not moving**: Check motor driver connections

### Serial Monitor
```bash
# View debug output
pio device monitor

# Or with Arduino IDE: Tools → Serial Monitor (115200 baud)
```