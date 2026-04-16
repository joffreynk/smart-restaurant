# Customer Ordering Kiosk - Hardware Setup

## Hardware Components
1. **Raspberry Pi 3B+** (or similar)
2. **Nokia 5110 LCD** (PCD8544 controller - 84x48 pixels)
3. **4x4 Matrix Keypad**
4. **Power supply** (5V 2A recommended)

---

## Wiring Diagram

### Nokia 5110 LCD
| LCD Pin | Function    | Raspberry Pi | BCM GPIO |
|---------|-------------|--------------|----------|
| VCC     | 3.3V Power  | Pin 1        | -        |
| GND     | Ground      | Pin 6        | -        |
| SCE     | Chip Select | Pin 15       | GPIO 22  |
| RST     | Reset       | Pin 16       | GPIO 23  |
| D/C     | Data/Cmd    | Pin 13       | GPIO 27  |
| MOSI    | SPI MOSI    | Pin 12       | GPIO 18  |
| SCLK    | SPI Clock   | Pin 11       | GPIO 17  |
| LED     | Backlight   | Pin 33       | GPIO 13  |

### 4x4 Keypad
| Row/Col | BCM GPIO | Physical Pin |
|---------|----------|--------------|
| R1      | GPIO 19  | Pin 35       |
| R2      | GPIO 26  | Pin 37       |
| R3      | GPIO 20  | Pin 38       |
| R4      | GPIO 21  | Pin 40       |
| C1      | GPIO 16  | Pin 36       |
| C2      | GPIO 12  | Pin 32       |
| C3      | GPIO 25  | Pin 22       |
| C4      | GPIO 24  | Pin 18       |

---

## Installation

```bash
# Install required packages
sudo apt-get update
sudo apt-get install python3-pip python3-rpi.gpio spidev

# Install Python dependencies
pip3 install flask python-socketio[client] eventlet

# Initialize database
cd master
python3 database/init_db.py

# Run the customer app
USE_HARDWARE=true python3 customer_interface/customer_app.py
```

---

## Keypad Functions

| Key | Function |
|-----|----------|
| `*` | Start order / Go to welcome |
| `1-5` | Select menu item |
| `A` | Next page |
| `B` | Previous page |
| `C` | Switch to Drinks |
| `D` | Go to Table selection |
| `#` | Cancel order / Go back |

---

## Order Flow

```
1. WELCOME SCREEN
   └─ "Welcome! Our Best Customer"
   └─ Press * to start

2. FOOD MENU (5 items per page)
   ├─ 1-5: Add item to cart
   ├─ A: Next page
   ├─ B: Previous page
   ├─ C: Switch to Drinks
   └─ D: Go to Table selection

3. DRINK MENU (5 items per page)
   ├─ 1-5: Add item to cart
   ├─ A: Next page
   ├─ B: Previous page
   ├─ C: Back to Food
   └─ D: Go to Table selection

4. TABLE SELECTION
   ├─ 1-5: Select table
   ├─ A: Next page
   ├─ B: Previous page
   └─ D: Confirm & show summary

5. CONFIRM ORDER
   ├─ Shows: Item count, Total, Table
   ├─ D: Send order (requires table + items)
   └─ #: Cancel and start over
```

---

## Testing

```bash
# Test all hardware
python3 customer_interface/test_hardware.py

# Test specific component
python3 customer_interface/test_hardware.py keypad
python3 customer_interface/test_hardware.py nokia
```

---

## Log Files

- **Key strokes**: `key_strokes.log` - Records all keypad presses with timestamp

---

## Running on Raspberry Pi

```bash
# Production mode
USE_HARDWARE=true python3 customer_interface/customer_app.py

# Without hardware (web only)
USE_HARDWARE=false python3 customer_interface/customer_app.py
```

## Running the App

```bash
# Run the customer kiosk interface (hardware + ordering)
python3 customer_interface/customer_app.py

# Access in browser
http://localhost:5001
```

---

## Real-Time Sync

The system uses WebSocket to sync data between all components:

| Event | When | Broadcast To |
|-------|------|--------------|
| `new_order` | Order placed (kiosk or API) | Dashboard, Robots |
| `kitchen_order` | New order for kitchen | All clients |
| `order_status_update` | Order status changed | All clients |
| `order_completed` | Order completed | All clients |

**Run main API first** (port 5000) so kiosk can connect:
```bash
python3 app.py
```

Then run kiosk (port 5001):
```bash
python3 customer_interface/customer_app.py
```

---

## Troubleshooting

### LCD not displaying
- Check SPI is enabled: `sudo raspi-config` → Interface Options → SPI
- Verify wiring connections
- Check 3.3V power supply

### Keypad not responding
- Check GPIO pin connections
- Verify pull-down resistors on columns
- Run: `python3 test_hardware.py keypad`

### Database error
- Run: `python3 database/init_db.py`
- Check schema.sql exists in database folder
