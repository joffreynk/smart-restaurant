# Raspberry Pi Master Controller

## Overview
Raspberry Pi 3B+ handles API server, WebSocket communication, database, and CCTV monitoring.

---

## Installation

```bash
cd master
pip install -r requirements.txt
```

### Requirements
```
Flask>=2.3.0
Flask-SocketIO>=5.3.0
SQLAlchemy>=2.0.0
Flask-SQLAlchemy>=3.0.0
python-socketio>=5.8.0
eventlet>=0.33.0
picamera>=1.13
picamera2>=0.3
opencv-python>=4.8.0
numpy>=1.24.0
pyserial>=3.5
RPi.GPIO>=0.7.0
spidev>=3.5
```

---

## Running

```bash
# Initialize database
python database/init_db.py

# Start API server (port 5000)
python app.py
```

---

## API Endpoints

### Robot Commands
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/robots/<id>/go-to-table/1` | POST | Send to Table 1 |
| `/api/robots/<id>/go-to-table/2` | POST | Send to Table 2 |
| `/api/robots/<id>/return-kitchen` | POST | Return home |
| `/api/robots/<id>/stop` | POST | Emergency stop |
| `/api/robots` | GET | List robots |

### Other Endpoints
| Endpoint | Description |
|----------|-------------|
| `/api/categories` | Menu categories |
| `/api/menu-items` | Menu items |
| `/api/orders` | Orders |
| `/api/tables` | Tables |
| `/health` | Health check |
| `/cv/start` | Start CCTV |
| `/cv/detections` | Get detections |

---

## Ports
| Service | Port |
|---------|------|
| API | 5000 |
| Customer Web | 5001 |
| Dashboard | 8080 |
| WebSocket | 8765 |

---

## CCTV Camera
- Used only for monitoring (no robot guidance)
- Access via `/cv/start` and `/cv/detections`

---

## Robot Communication

Pi communicates with REX via **WebSocket** (port 8765):

```json
// Send command
{"type":"COMMAND","data":{"action":"go_to_table_1"}}

// Receive telemetry
{"type":"TELEMETRY","device_id":"ROBOT-001","data":{...}}
```