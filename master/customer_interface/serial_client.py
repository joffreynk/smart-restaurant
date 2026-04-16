import serial
import threading
import time
import json
import logging
from datetime import datetime

logging.basicConfig(
    filename='key_strokes.log',
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class CustomerInterfaceClient:
    def __init__(self, port='/dev/ttyUSB0', baudrate=9600):
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        self.connected = False
        self.running = False
        self.thread = None
        self.callbacks = []
        self.buffer = ""
        
    def connect(self):
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=1,
                write_timeout=1
            )
            self.connected = True
            self.running = True
            self.thread = threading.Thread(target=self._read_loop, daemon=True)
            self.thread.start()
            print(f"Connected to customer interface on {self.port}")
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        if self.serial and self.serial.is_open:
            self.serial.close()
        self.connected = False
    
    def _read_loop(self):
        while self.running:
            try:
                if self.serial and self.serial.in_waiting > 0:
                    data = self.serial.read(self.serial.in_waiting).decode('utf-8', errors='ignore')
                    self.buffer += data
                    
                    while '\n' in self.buffer:
                        line, self.buffer = self.buffer.split('\n', 1)
                        line = line.strip()
                        if line:
                            self._process_message(line)
                else:
                    time.sleep(0.1)
            except Exception as e:
                print(f"Read error: {e}")
                time.sleep(1)
    
    def _process_message(self, message):
        try:
            data = json.loads(message)
            msg_type = data.get('type', 'unknown')
            
            for callback in self.callbacks:
                try:
                    callback(msg_type, data)
                except Exception as e:
                    print(f"Callback error: {e}")
                    
            if msg_type == 'key_pressed':
                self._handle_key_press(data)
            elif msg_type == 'request_menu':
                self._send_menu_data()
            elif msg_type == 'request_tables':
                self._send_tables_data()
                
        except json.JSONDecodeError:
            print(f"Invalid JSON: {message}")
    
    def _handle_key_press(self, data):
        key = data.get('key', '')
        logger.info(f"Key pressed: {key}")
        print(f"Key pressed: {key}")
    
    def _send_menu_data(self):
        self.send_command('menu_data', {
            'categories': [
                {'id': 1, 'name': 'Appetizers'},
                {'id': 2, 'name': 'Main Courses'},
                {'id': 3, 'name': 'Desserts'},
                {'id': 4, 'name': 'Beverages'}
            ]
        })
    
    def _send_tables_data(self):
        self.send_command('tables_data', {
            'tables': [
                {'id': 1, 'number': 1, 'status': 'free'},
                {'id': 2, 'number': 2, 'status': 'free'},
                {'id': 3, 'number': 3, 'status': 'free'},
                {'id': 4, 'number': 4, 'status': 'free'},
                {'id': 5, 'number': 5, 'status': 'free'}
            ]
        })
    
    def send_command(self, command, data=None):
        if not self.connected or not self.serial:
            return False
        
        try:
            message = {'type': command, 'timestamp': datetime.utcnow().isoformat()}
            if data:
                message['data'] = data
            
            json_str = json.dumps(message) + '\n'
            self.serial.write(json_str.encode('utf-8'))
            return True
        except Exception as e:
            print(f"Send error: {e}")
            return False
    
    def register_callback(self, callback):
        self.callbacks.append(callback)
    
    def display_message(self, message, line=0):
        self.send_command('display', {'text': message, 'line': line})
    
    def display_menu_item(self, name, price, description=""):
        self.send_command('menu_item', {'name': name, 'price': price, 'description': description})
    
    def display_table_status(self, table_number, status):
        self.send_command('table_status', {'table': table_number, 'status': status})
    
    def request_order_confirmation(self, items, total):
        self.send_command('confirm_order', {'items': items, 'total': total})
    
    def clear_display(self):
        self.send_command('clear', {})


customer_interface = None

def get_customer_interface(port='/dev/ttyUSB0', baudrate=9600):
    global customer_interface
    if customer_interface is None:
        customer_interface = CustomerInterfaceClient(port, baudrate)
    return customer_interface