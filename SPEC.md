# Restaurant Service Automation - System Specification

## Updated Architecture (PC-Based Master + Phone + Robots)

### Core Change
- **Master Controller**: Now runs on desktop/laptop computer (NOT Raspberry Pi)
- **Customer Interface**: Phone app via WebSocket (specific registered phones only)
- **Order Flow**: Customer phone -> Master confirms -> Robot gets order

---

## System Components

### 1. Master Controller (PC Server)
- **Host**: Main computer (desktop/laptop)
- **Port**: 5000
- **Database**: SQLite (restaurant.db)
- **Functions**:
  - Accepts orders ONLY from registered phones
  - Confirms/rejects orders manually
  - Controls robot assignments after confirmation
  - Manages menu, tables, orders

### 2. Customer Phone Client
- **Connection**: WebSocket to master (port 5000)
- **Registration**: Admin registers phone unique_id
- **Order Flow**:
  1. Customer orders food on phone
  2. Selects drinks
  3. Selects table
  4. Submits order to master
  5. **WAITS for master confirmation**
  6. After confirmation, robot delivers

### 3. Robot Client (ESP32)
- **Connection**: WebSocket to master
- **Registration**: Unique ID registered by admin
- **Function**: Delivers only AFTER master confirms order

---

## Order Flow Diagram

```
Phone (customer)
    |
    |--[order_submit]--> WebSocket --> Master Controller
    |                                          |
    |                                   [MASTER CONFIRMS/REJECTS]
    |                                          |
    |<--[order_confirmed/rejected]-- WebSocket --+
    |
    |                            [Robot gets command]
    |                                  |
    +-------- WebSocket <---[robot_command]---+
```

---

## WebSocket Events

### Phone -> Master
| Event | Description |
|-------|------------|
| `phone_register` | Register phone with unique_id |
| `order_submit` | Submit order (food_items, drink_items, table_number) |
| `order_cancel` | Cancel pending order |

### Master -> Phone
| Event | Description |
|-------|------------|
| `registered` | Phone registration response |
| `order_confirmed` | Order approved by master |
| `order_rejected` | Order rejected (reason provided) |
| `preparing_status` | Order being prepared |
| `ready_status` | Order ready for pickup |
| `kitchen_order` | Kitchen receives order |

### Master -> Robot
| Event | Description |
|-------|------------|
| `robot_command` | Navigate, pick up, deliver |
| `delivery_update` | Delivery status change |

### Robot -> Master
| Event | Description |
|-------|------------|
| `robot_status` | Current robot status |
| `robot_telemetry` | Battery, position |
| `delivery_update` | Delivery progress |

---

## REST API Endpoints

### Phone Management
- `POST /api/phones/register` - Register new phone
- `GET /api/phones` - List registered phones
- `DELETE /api/phones/<id>` - Remove phone

### Orders
- `GET /api/orders` - List orders
- `POST /api/orders` - Create order (from phone)
- `PUT /api/orders/<id>` - Update status
- `POST /api/orders/<id>/confirm` - Confirm order (MASTER ONLY)
- `POST /api/orders/<id>/reject` - Reject order (MASTER ONLY)

### Menu & Tables (existing)
- `GET /api/categories`
- `GET /api/menu-items`
- `GET /api/tables`
- `GET /api/tables/available`

### Robots (existing)
- `GET /api/robots`
- `POST /api/robots/:id/command`

---

## Database Schema (Updated)

### phones table
| Column | Type | Constraints |
|--------|------|------------|
| id | INTEGER | PRIMARY KEY |
| unique_id | TEXT | NOT NULL UNIQUE |
| customer_name | TEXT | |
| is_active | BOOLEAN | DEFAULT 1 |
| created_at | DATETIME | |

### orders table (additions)
| Column | Type | Constraints |
|--------|------|------------|
| phone_id | INTEGER | FOREIGN KEY -> phones(id) |
| status | TEXT | pending/confirmed/preparing/ready/delivered/completed |
| confirmed_at | DATETIME | NULLABLE |
| rejected_at | DATETIME | NULLABLE |
| rejection_reason | TEXT | NULLABLE |

---

## Directory Structure

```
/restaurant/
├── master/
│   ├── app.py                    # Flask app (runs on PC)
│   ├── config.py
│   ├── api/
│   │   ├── routes.py           # REST API
│   │   └── webSocket.py       # WebSocket handlers
│   ├── database/
│   │   ├── schema.sql
│   │   ├── init_db.py
│   │   └── models.py
│   ├── dashboard/
│   │   ├── app.py            # Admin dashboard
│   │   └── templates/
│   └── requirements.txt
│
├── phone/
│   └── index.html            # Phone client app
│
└── waiter/
    └── src/main.cpp         # Robot code (ESP32)
```

---

## Phone Client HTML Structure

The phone client runs as a web app:
1. **Landing**: Enter phone ID to connect
2. **Menu**: Browse food categories
3. **Drinks**: Browse drinks
4. **Tables**: Select available table
5. **Cart**: Review order
6. **Submit**: Send to master
7. **Wait**: Show confirmation status

---

## Technology Stack

- **Master**: Python Flask + Flask-SocketIO (runs on PC)
- **Phone Client**: HTML/JS with Socket.IO client
- **Robot**: C++ ESP32 with Socket.IO client
- **Database**: SQLite

---

## Configuration

```python
# Master (PC)
API_PORT = 5000
WEBSOCKET_PORT = 5000
DATABASE_PATH = 'restaurant.db'

# Phone Client
WS_SERVER_URL = 'http://192.168.x.x:5000'  # PC IP address

# Robot
ROBOT_SERVER_URL = 'http://192.168.x.x:5000'  # PC IP address
```