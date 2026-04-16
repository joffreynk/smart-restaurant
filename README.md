# Autonomous Smart Restaurant System

## Overview
This is a comprehensive IoT-based restaurant automation system using Raspberry Pi 3B+ as the central master controller, coordinating autonomous waiter robots and customer self-service interfaces.

---

## System Architecture

### Hardware Components

| Component | Model | Purpose |
|-----------|-------|---------|
| Master Controller | Raspberry Pi 3B+ | Central hub, database, API server |
| Camera | Pi Camera v2 (8MP) | Computer vision for table detection |
| Waiter Robots | Omni-Directional (ESP32) | Autonomous food delivery |
| Customer Interface (Web) | Pi Web Server (port 5001) | Self-service ordering |
| Customer Interface (Hardware) | Pi + 4x4 Keypad + Nokia LCD 5110 | Physical keypad/LCD terminal |

### Network Topology
```
[Master RP3B+]
    ├── WiFi ──► [Robot 1 (ESP32)]
    │           └── Ultrasonic + Omni Motors + Battery
    ├── WiFi ──► [Robot 2 (ESP32)]
    │           └── Ultrasonic + Omni Motors + Battery
    ├── HTTP (5000) ──► API Server
    ├── HTTP (5001) ──► Customer Web Interface
    └── HTTP (8080) ──► Admin Dashboard
    
[Hardware Interface]
    └── GPIO ──► 4x4 Keypad + Nokia LCD 5110
```

---

## Project Structure

```
restaurant/
├── SPEC.md                    # Technical specification
├── README.md                  # This file
├── master/                    # Raspberry Pi Controller
│   ├── app.py                # Flask + SocketIO server
│   ├── config.py             # Configuration settings
│   ├── requirements.txt      # Python dependencies
│   ├── database/             # SQLite database
│   │   ├── schema.sql         # Database schema
│   │   ├── init_db.py         # DB initialization
│   │   └── models.py         # SQLAlchemy models
│   ├── api/                   # REST API
│   │   ├── routes.py          # API endpoints
│   │   └── webSocket.py       # Real-time WebSocket
│   ├── services/              # Business logic
│   │   ├── cv_service.py      # Computer vision
│   │   ├── robot_manager.py   # Robot coordination
│   │   ├── navigation.py      # Path planning
│   │   └── order_service.py   # Order processing
│   ├── customer_interface/    # Customer terminal
│   │   ├── customer_app.py   # Web-based (port 5001)
│   │   ├── hardware_interface.py  # Keypad + LCD
│   │   └── serial_client.py   # Serial (legacy)
│   └── dashboard/             # Admin web interface
│       ├── app.py             # Dashboard Flask app
│       └── templates/         # HTML templates
└── waiter/                   # ESP32 Waiter Robot
    ├── platformio.ini         # PlatformIO config
    ├── include/config.h       # Robot configuration
    └── src/main.cpp           # Robot firmware
```

---

## Database Schema

### Tables (Normalized)

1. **categories** - Food categories (Appetizers, Main, Desserts, Beverages)
2. **menu_items** - Menu items with prices and descriptions
3. **tables** - Restaurant tables with positions
4. **table_status** - Real-time occupancy status
5. **orders** - Customer orders
6. **order_items** - Order line items
7. **robots** - Waiter robot status and telemetry
8. **delivery_records** - Order delivery tracking
9. **navigation_paths** - Learned navigation routes
10. **telemetry_history** - Robot telemetry log

---

## REST API Endpoints

### Categories
- `GET /api/categories` - List all categories
- `POST /api/categories` - Create category
- `PUT /api/categories/:id` - Update category
- `DELETE /api/categories/:id` - Delete category

### Menu Items
- `GET /api/menu-items` - List menu items
- `GET /api/menu-items/category/:id` - Items by category
- `POST /api/menu-items` - Create item
- `PUT /api/menu-items/:id` - Update item
- `DELETE /api/menu-items/:id` - Delete item

### Tables
- `GET /api/tables` - List all tables
- `GET /api/tables/available` - Available tables
- `POST /api/tables/:id/reserve` - Reserve table
- `POST /api/tables/:id/release` - Release table

### Orders
- `GET /api/orders` - List orders
- `GET /api/orders/active` - Active orders
- `POST /api/orders` - Create order
- `PUT /api/orders/:id` - Update order
- `POST /api/orders/:id/complete` - Complete order

### Robots
- `GET /api/robots` - List robots
- `GET /api/robots/:id/analytics` - Robot statistics
- `PUT /api/robots/:id/telemetry` - Update telemetry
- `PUT /api/robots/:id/status` - Update status

### Dashboard
- `GET /api/dashboard/stats` - Dashboard statistics
- `GET /api/analytics/serving-time` - Robot performance
- `GET /api/analytics/orders-by-hour` - Order trends

---

## WebSocket Communication

### Message Types

**TELEMETRY (Robot → Master)**
```json
{
  "type": "TELEMETRY",
  "device_id": "ROBOT-001",
  "data": {
    "battery_voltage": 3.85,
    "battery_percentage": 78,
    "current_x": 2.5,
    "current_y": 3.2,
    "current_angle": 45.5,
    "status": "delivering"
  }
}
```

**COMMAND (Master → Robot)**
```json
{
  "type": "COMMAND",
  "device_id": "ROBOT-001",
  "data": {
    "action": "navigate_to_table",
    "target_x": 1.5,
    "target_y": 2.0,
    "path": [...]
  }
}
```

**STATUS (Bidirectional)**
```json
{
  "type": "STATUS",
  "device_id": "ROBOT-001",
  "data": {
    "status": "delivering",
    "order_id": 15
  }
}
```

**ACK (Bidirectional)**
```json
{
  "type": "ACK",
  "device_id": "ROBOT-001",
  "data": {
    "command_id": "cmd-12345",
    "success": true
  }
}
```

---

## Admin Dashboard Pages

| Page | URL | Description |
|------|-----|-------------|
| Login | `/login` | Admin authentication |
| Dashboard | `/dashboard` | Overview statistics |
| Menu | `/menu` | Category & item CRUD |
| Orders | `/orders` | Order management |
| Tables | `/tables` | Table status |
| Robot Telemetry | `/robots` | Real-time robot monitoring |
| Robot Subscription | `/robot-subscription` | Register new robots |
| Analytics | `/analytics` | Performance charts |

**Login Credentials:** admin / admin123

---

## Installation & Running

### Master Controller (Raspberry Pi)

```bash
# Install dependencies
cd master
pip install -r requirements.txt

# Initialize database
python database/init_db.py

# Start API server (port 5000)
python app.py

# Start customer interface (port 5001) - separate terminal
python customer_interface/customer_app.py

# Start dashboard (port 8080) - separate terminal
python dashboard/app.py
```

### Waiter Robot (ESP32)

```bash
# Install PlatformIO
# Upload the code using PlatformIO IDE or CLI
cd waiter
pio run --target upload

# Or flash via Arduino IDE with ESP32 board
```

### Hardware Interface (4x4 Keypad + Nokia LCD)

#### Pin Configuration

**Nokia 5110 LCD:**
| LCD Pin | Function | Raspberry Pi GPIO | Physical Pin |
|---------|----------|-------------------|--------------|
| VCC | 3.3V | 3.3V | Pin 1 |
| GND | Ground | GND | Pin 6 |
| SCE | Chip Select | GPIO 18 | Pin 12 |
| RST | Reset | GPIO 23 | Pin 16 |
| D/C | Data/Command | GPIO 24 | Pin 18 |
| MOSI | SPI MOSI | GPIO 10 | Pin 19 |
| SCLK | SPI Clock | GPIO 11 | Pin 23 |
| LED | Backlight | GPIO 13 | Pin 33 |

**4x4 Keypad (Matrix):**
| Row/Col | GPIO Pin | Physical Pin |
|---------|----------|--------------|
| R1 (Row 1) | GPIO 17 | Pin 11 |
| R2 (Row 2) | GPIO 27 | Pin 13 |
| R3 (Row 3) | GPIO 22 | Pin 15 |
| R4 (Row 4) | GPIO 5 | Pin 29 |
| C1 (Col 1) | GPIO 6 | Pin 31 |
| C2 (Col 2) | GPIO 13 | Pin 33 |
| C3 (Col 3) | GPIO 19 | Pin 35 |
| C4 (Col 4) | GPIO 26 | Pin 37 |

```bash
# Run hardware interface (requires root)
sudo python customer_interface/customer_app.py
```

---

## Robot AI Speed Control

The robot uses 1 ultrasonic sensor (HC-SR04 on REX shared header) with AI speed zones:

| Distance | Speed | Zone |
|----------|-------|------|
| >100cm | 100% (150) | FAR |
| 50-100cm | 70% (105) | MEDIUM |
| 30-50cm | 40% (60) | CLOSE |
| 15-30cm | 20% (30) | DANGER |
| <15cm | 0% (stop) | STOP |

### Obstacle Avoidance (Single Sensor)
- Front: Primary forward distance measurement
- Left/Right scan: Robot rotates 45° to scan sides when needed
- If blocked: Request direction from master

---

## Customer Interface Flow

1. **Idle State**: Display "Press # to order"
2. **Main Menu**: Press # → Shows categories (1-4)
3. **Select Category**: Choose category → Shows items
4. **Select Item**: Choose item → Enter quantity (1-9)
5. **Cart**: Press * to checkout
6. **Confirm**: Press # to place order
7. **Table Reservation**: Press * on idle → Enter name, phone, party size

---

## Robot Navigation States

```
IDLE → ASSIGNED → PICKING_UP → DELIVERING → SERVING → RETURNING → IDLE
         ↓                                          ↓
      CHARGING ←────────────────────────────── CHARGING
         ↓
      ERROR → MAINTENANCE
```

---

## Security Considerations

- WPA2-PSK WiFi encryption
- JWT token authentication for API
- Input validation on all endpoints
- Parameterized SQL queries (SQL injection prevention)
- Rate limiting on API endpoints

---

## System Features

✅ Real-time table status monitoring via computer vision  
✅ Autonomous robot navigation with AI speed control  
✅ Omni-directional robot movement  
✅ WiFi-based real-time master-waiter communication  
✅ WebSocket for instant state synchronization  
✅ SQLite database with normalized tables  
✅ Responsive admin dashboard  
✅ Customer web-based self-service ordering (port 5001)  
✅ Customer hardware interface (4x4 Keypad + Nokia LCD)  
✅ Order tracking with robot delivery attribution  
✅ Serving time analytics per robot  
✅ Navigation path learning and optimization  

---

## License
MIT License - Educational Purpose