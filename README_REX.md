# Waiter Robot - REX Edition

## Overview
Autonomous waiter robot using REX 8in1 (ESP32) with line following and color junction detection.

---

## Arduino IDE Setup

### Board Manager
1. File > Preferences > Additional Boards Manager URLs:
```
https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
```
2. Tools > Board > Boards Manager > install "esp32"

### Libraries
| Library | Search |
|---------|--------|
| WebSockets | by Links2004 |
| ArduinoJson | by Benoit Blanchon |
| DabbleESP32 | by Robotistan |

---

## Pin Configuration (REX 8in1)

| Component | GPIO | Notes |
|-----------|------|-------|
| Motor A | 15, 23 | PWM |
| Motor B | 32, 33 | PWM |
| Motor C | 5, 4 | PWM |
| Motor D | 27, 14 | PWM |
| IR Line | 35, 36, 39 | |
| Color Sensor | 34,26,27,14,13 | TCS3200 |
| Ultrasonic | 17, 16 | |
| Buzzer | 25 | |
| Battery | 34 | Analog |

---

## Commands

| Action | Description |
|--------|-------------|
| `go_to_table_1` | Deliver to Table 1 |
| `go_to_table_2` | Deliver to Table 2 |
| `return_to_kitchen` | Return home |
| `stop` | Rotate 360°, wait |
| `resume` | Resume line following |

---

## Floor Layout

```
         [Kitchen]
            |
       WHITE LINE
            |
       [COLOR] ← blue or black
          /    \
    LEFT       RIGHT
      |         |
  Table 1   Table 2
```

## Junction Logic

**ONE color marker** (blue OR black):
- Robot detects color → stops at junction
- Uses `originTable` to decide turn:
  - From table_1 → turn LEFT → kitchen
  - From table_2 → turn RIGHT → kitchen
  - Going to table_1 → turn LEFT
  - Going to table_2 → turn RIGHT

---

## WiFi Config
```cpp
const char* WIFI_SSID = "RestaurantWiFi";
const char* WIFI_PASSWORD = "restaurant2026";
const char* MASTER_IP = "192.168.1.100";
const uint16_t MASTER_PORT = 8765;
```

---

## Robot Number
```cpp
#define ROBOT_NUMBER 1  // or 2
```

---

## Upload
1. Tools > Board > ESP32 WROOM-32
2. Tools > Port > COMX
3. Sketch > Upload