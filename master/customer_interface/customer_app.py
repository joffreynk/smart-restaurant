"""
Customer Self-Service Interface
Runs on Raspberry Pi 3B+ - Hardware (LCD + Keypad) ordering terminal

State Machine Flow:
- WELCOME: Show "Welcome our best customer" -> press * to start
- FOOD_MENU: Show food items 1-5 -> press 1-5 to add -> A=next, B=prev
- DRINK_MENU: Show drinks 1-5 -> press 1-5 to add -> A=next, B=prev
- SELECT_TABLE: Show available tables -> press 1-5 to select
- CONFIRM: Show order summary -> D to send, # to cancel

WebSocket: Connects to main API (port 5000) to broadcast events
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from datetime import datetime
import sqlite3
import os
import threading
import socketio

USE_HARDWARE = os.environ.get('USE_HARDWARE', 'true').lower() == 'true'
WS_SERVER_URL = os.environ.get('WS_SERVER_URL', 'http://localhost:5000')

hw_interface = None
hw_thread = None
hw_running = False
socketio_client = None

if USE_HARDWARE:
    try:
        import sys
        sys.path.insert(0, os.path.dirname(__file__))
        from hardware_interface import get_hardware_interface, Keypad4x4, Nokia5110LCD
    except ImportError as e:
        print(f"Hardware import failed: {e}")
        USE_HARDWARE = False

app = Flask(__name__, template_folder='../dashboard/templates')
app.secret_key = 'restaurant-customer-2026'

DATABASE_PATH = os.path.join(os.path.dirname(__file__), '..', 'database', 'restaurant.db')

def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


class OrderState:
    WELCOME = 'welcome'
    FOOD_MENU = 'food_menu'
    DRINK_MENU = 'drink_menu'
    SELECT_TABLE = 'select_table'
    CONFIRM_ORDER = 'confirm_order'


class CustomerOrderMachine:
    def __init__(self):
        self.state = OrderState.WELCOME
        self.cart = []
        self.selected_table = None
        self.categories = []
        self.current_category_idx = 0
        self.menu_page = 0
        self.items_per_page = 5
        
    def reset(self):
        self.state = OrderState.WELCOME
        self.cart = []
        self.selected_table = None
        self.current_category_idx = 0
        self.menu_page = 0
        
    def load_categories(self, conn):
        self.categories = conn.execute('SELECT id, name FROM categories ORDER BY id').fetchall()
        
    def get_current_category_id(self):
        if self.current_category_idx < len(self.categories):
            return self.categories[self.current_category_idx]['id']
        return None
    
    def load_menu_items(self, conn):
        category_id = self.get_current_category_id()
        if not category_id:
            return []
        items = conn.execute('''
            SELECT id, name, price FROM menu_items 
            WHERE category_id = ? AND is_available = 1
            ORDER BY id LIMIT ? OFFSET ?
        ''', (category_id, self.items_per_page, self.menu_page * self.items_per_page)).fetchall()
        return items
    
    def get_total(self, conn):
        total = 0
        for item in self.cart:
            price = conn.execute('SELECT price FROM menu_items WHERE id = ?', 
                              (item['menu_item_id'],)).fetchone()
            if price:
                total += price['price'] * item['quantity']
        return total
    
    def load_tables(self, conn):
        tables = conn.execute('''
            SELECT t.id, t.table_number, t.capacity,
                   COALESCE(ts.status, 'free') as status
            FROM tables t
            LEFT JOIN table_status ts ON t.id = ts.table_id
            WHERE t.is_active = 1
            ORDER BY t.table_number
            LIMIT 5 OFFSET ?
        ''', (self.menu_page * 5,)).fetchall()
        return tables


def find_category_index(conn, name):
    categories = conn.execute('SELECT name FROM categories ORDER BY id').fetchall()
    for i, cat in enumerate(categories):
        if cat['name'].lower() == name.lower():
            return i
    return 0


order_machine = CustomerOrderMachine()


def broadcast_order(order_id, total, items, table_number):
    print(f"[DEBUG] Broadcasting order #{order_id}")
    if socketio_client and socketio_client.connected:
        print("[DEBUG] SocketIO connected, emitting new_order")
        items_data = []
        for item in items:
            items_data.append({
                'name': item['name'],
                'quantity': item['quantity'],
                'price': item['price']
            })
        
        socketio_client.emit('new_order', {
            'order_id': order_id,
            'table_number': table_number,
            'total': total,
            'items': items_data,
            'timestamp': datetime.utcnow().isoformat()
        }, broadcast=True)
        print(f"[DEBUG] Broadcasted new order #{order_id}")
    else:
        print("[DEBUG] SocketIO not connected, skipping broadcast")


def setup_websocket():
    global socketio_client
    import socketio as sio
    
    print(f"[DEBUG] Setting up WebSocket to: {WS_SERVER_URL}")
    
    try:
        socketio_client = sio.Client()
        
        @socketio_client.on('connect')
        def on_connect():
            print(f"[DEBUG] Connected to WebSocket server")
        
        @socketio_client.on('disconnect')
        def on_disconnect():
            print("[DEBUG] Disconnected from WebSocket server")
        
        @socketio_client.on('order_status_update')
        def on_order_update(data):
            print(f"[DEBUG] Order status update: {data}")
        
        socketio_client.connect(WS_SERVER_URL)
        return True
        
    except Exception as e:
        print(f"[DEBUG] WebSocket connection failed: {e}")
        socketio_client = None
        return False


def display_welcome():
    if not hw_interface:
        print("[DEBUG] No hardware interface")
        return
    print("[DEBUG] Displaying welcome screen")
    hw_interface.lcd.clear()
    print("[DEBUG] LCD cleared")
    hw_interface.lcd.text("Welcome!", 0, 0)
    print("[DEBUG] Line 0: Welcome!")
    hw_interface.lcd.text("Our Best Customer", 0, 2)
    print("[DEBUG] Line 2: Our Best Customer")
    hw_interface.lcd.text("Press * to start", 0, 5)
    print("[DEBUG] Line 5: Press * to start")
    print("[DEBUG] Welcome screen complete")


def display_food_menu(conn):
    if not hw_interface:
        return
    hw_interface.lcd.clear()
    cat_name = order_machine.categories[order_machine.current_category_idx]['name'] if order_machine.current_category_idx < len(order_machine.categories) else "Food"
    hw_interface.lcd.text(f"{cat_name[:14]}", 0, 0)
    
    items = order_machine.load_menu_items(conn)
    for i, item in enumerate(items):
        hw_interface.lcd.text(f"{i+1}.{item['name'][:10]} ${item['price']}", 0, i+1)
    hw_interface.lcd.text("A:Next B:Prev C:Drink", 0, 5)


def display_drink_menu(conn):
    if not hw_interface:
        return
    hw_interface.lcd.clear()
    cat_name = order_machine.categories[order_machine.current_category_idx]['name'] if order_machine.current_category_idx < len(order_machine.categories) else "Drinks"
    hw_interface.lcd.text(f"{cat_name[:14]}", 0, 0)
    
    items = order_machine.load_menu_items(conn)
    for i, item in enumerate(items):
        hw_interface.lcd.text(f"{i+1}.{item['name'][:10]} ${item['price']}", 0, i+1)
    hw_interface.lcd.text("A:Next B:Prev D:Table", 0, 5)


def display_table_selection(conn):
    if not hw_interface:
        return
    hw_interface.lcd.clear()
    hw_interface.lcd.text("Select Table:", 0, 0)
    
    tables = order_machine.load_tables(conn)
    for i, table in enumerate(tables):
        status = table['status']
        hw_interface.lcd.text(f"{i+1}.T{table['table_number']} ({status})", 0, i+1)
    hw_interface.lcd.text("A:Next B:Prev D:Confirm", 0, 5)


def display_confirm(conn):
    if not hw_interface:
        return
    hw_interface.lcd.clear()
    hw_interface.lcd.text(f"Items: {len(order_machine.cart)}", 0, 0)
    total = order_machine.get_total(conn)
    hw_interface.lcd.text(f"Total: ${total:.2f}", 0, 1)
    
    if order_machine.selected_table:
        hw_interface.lcd.text(f"Table: {order_machine.selected_table}", 0, 2)
    else:
        hw_interface.lcd.text("No table selected!", 0, 2)
    
    hw_interface.lcd.text("D:Send #:Cancel", 0, 5)


def handle_welcome(key):
    if key == '*':
        order_machine.state = OrderState.FOOD_MENU
        conn = get_db()
        order_machine.load_categories(conn)
        display_food_menu(conn)
        conn.close()
        return True
    return False


def find_category_index(conn, name):
    categories = conn.execute('SELECT name FROM categories ORDER BY id').fetchall()
    for i, cat in enumerate(categories):
        if cat['name'].lower() == name.lower():
            return i
    return 0


def handle_food_menu(key, conn):
    items = order_machine.load_menu_items(conn)
    
    if key in '12345' and int(key) <= len(items):
        item = items[int(key) - 1]
        order_machine.cart.append({
            'menu_item_id': item['id'],
            'name': item['name'],
            'price': item['price'],
            'quantity': 1
        })
        hw_interface.lcd.clear()
        hw_interface.lcd.text(f"Added: {item['name'][:14]}", 0, 2)
        return True
    
    elif key == 'A':
        order_machine.menu_page += 1
        if not items:
            order_machine.menu_page = 0
        display_food_menu(conn)
        return True
    
    elif key == 'B':
        order_machine.menu_page = max(0, order_machine.menu_page - 1)
        display_food_menu(conn)
        return True
    
    elif key == 'C':
        order_machine.state = OrderState.DRINK_MENU
        order_machine.current_category_idx = find_category_index(conn, 'Beverages')
        order_machine.menu_page = 0
        display_drink_menu(conn)
        return True
    
    elif key == 'D':
        if order_machine.cart:
            order_machine.state = OrderState.SELECT_TABLE
            order_machine.menu_page = 0
            display_table_selection(conn)
        else:
            hw_interface.lcd.clear()
            hw_interface.lcd.text("Cart is empty!", 0, 2)
            hw_interface.lcd.text("Add food first", 0, 4)
        return True
    
    return False


def find_category_index(conn, name):
    categories = conn.execute('SELECT name FROM categories ORDER BY id').fetchall()
    for i, cat in enumerate(categories):
        if cat['name'].lower() == name.lower():
            return i
    return 0


def handle_drink_menu(key, conn):
    items = order_machine.load_menu_items(conn)
    
    if key in '12345' and int(key) <= len(items):
        item = items[int(key) - 1]
        order_machine.cart.append({
            'menu_item_id': item['id'],
            'name': item['name'],
            'price': item['price'],
            'quantity': 1
        })
        hw_interface.lcd.clear()
        hw_interface.lcd.text(f"Added: {item['name'][:14]}", 0, 2)
        return True
    
    elif key == 'A':
        order_machine.menu_page += 1
        if not items:
            order_machine.menu_page = 0
        display_drink_menu(conn)
        return True
    
    elif key == 'B':
        order_machine.menu_page = max(0, order_machine.menu_page - 1)
        display_drink_menu(conn)
        return True
    
    elif key == 'C':
        order_machine.state = OrderState.FOOD_MENU
        order_machine.current_category_idx = find_category_index(conn, 'Appetizers')
        order_machine.menu_page = 0
        display_food_menu(conn)
        return True
    
    elif key == 'D':
        order_machine.state = OrderState.SELECT_TABLE
        order_machine.menu_page = 0
        display_table_selection(conn)
        return True
    
    return False


def handle_table_selection(key, conn):
    tables = order_machine.load_tables(conn)
    
    if key in '12345' and int(key) <= len(tables):
        table = tables[int(key) - 1]
        if table['status'] == 'free':
            order_machine.selected_table = table['table_number']
            order_machine.state = OrderState.CONFIRM_ORDER
            display_confirm(conn)
        else:
            hw_interface.lcd.clear()
            hw_interface.lcd.text(f"Table {table['table_number']}", 0, 0)
            hw_interface.lcd.text("is not available", 0, 2)
        return True
    
    elif key == 'A':
        order_machine.menu_page += 1
        display_table_selection(conn)
        return True
    
    elif key == 'B':
        order_machine.menu_page = max(0, order_machine.menu_page - 1)
        display_table_selection(conn)
        return True
    
    elif key == 'D':
        if order_machine.selected_table:
            order_machine.state = OrderState.CONFIRM_ORDER
            display_confirm(conn)
        else:
            hw_interface.lcd.clear()
            hw_interface.lcd.text("Select a table!", 0, 2)
        return True
    
    return False


def handle_confirm_order(key, conn):
    if key == 'D':
        if not order_machine.selected_table:
            hw_interface.lcd.clear()
            hw_interface.lcd.text("Select table first!", 0, 2)
            order_machine.state = OrderState.SELECT_TABLE
            display_table_selection(conn)
            return True
        
        if not order_machine.cart:
            hw_interface.lcd.clear()
            hw_interface.lcd.text("Cart is empty!", 0, 2)
            order_machine.state = OrderState.FOOD_MENU
            display_food_menu(conn)
            return True
        
        table = conn.execute('SELECT id FROM tables WHERE table_number = ?', 
                           (order_machine.selected_table,)).fetchone()
        
        cursor = conn.cursor()
        total = order_machine.get_total(conn)
        
        cursor.execute('''
            INSERT INTO orders (table_id, total_amount, customer_name, customer_phone, status, created_at)
            VALUES (?, ?, ?, ?, 'pending', ?)
        ''', (table['id'], total, 'Guest', '', datetime.utcnow().isoformat()))
        
        order_id = cursor.lastrowid
        
        for item in order_machine.cart:
            subtotal = item['price'] * item['quantity']
            cursor.execute('''
                INSERT INTO order_items (order_id, menu_item_id, quantity, unit_price, subtotal)
                VALUES (?, ?, ?, ?, ?)
            ''', (order_id, item['menu_item_id'], item['quantity'], item['price'], subtotal))
        
        conn.commit()
        
        broadcast_order(order_id, total, order_machine.cart, order_machine.selected_table)
        
        hw_interface.lcd.clear()
        hw_interface.lcd.text("Order Sent!", 0, 2)
        hw_interface.lcd.text(f"Order #{order_id}", 0, 4)
        
        order_machine.reset()
        return True
    
    elif key == '#':
        hw_interface.lcd.clear()
        hw_interface.lcd.text("Order Cancelled", 0, 2)
        order_machine.reset()
        display_welcome()
        return True
    
    return False


def process_keypress(key):
    if not USE_HARDWARE or not hw_interface:
        return
    
    conn = get_db()
    
    if key == '#':
        if order_machine.state != OrderState.WELCOME:
            hw_interface.lcd.clear()
            hw_interface.lcd.text("Going back...", 0, 2)
            order_machine.reset()
            display_welcome()
            conn.close()
            return
    
    if order_machine.state == OrderState.WELCOME:
        handle_welcome(key)
    
    elif order_machine.state == OrderState.FOOD_MENU:
        handle_food_menu(key, conn)
    
    elif order_machine.state == OrderState.DRINK_MENU:
        handle_drink_menu(key, conn)
    
    elif order_machine.state == OrderState.SELECT_TABLE:
        handle_table_selection(key, conn)
    
    elif order_machine.state == OrderState.CONFIRM_ORDER:
        handle_confirm_order(key, conn)
    
    conn.close()


@app.route('/')
def index():
    session.clear()
    return render_template('customer_home.html')

@app.route('/order')
def order_page():
    conn = get_db()
    categories = conn.execute('SELECT * FROM categories WHERE is_active IS NOT 0 OR is_active IS NULL ORDER BY display_order, id').fetchall()
    conn.close()
    return render_template('customer_order.html', categories=categories)

@app.route('/api/customer/menu/<int:category_id>')
def get_category_menu(category_id):
    conn = get_db()
    items = conn.execute('''
        SELECT id, name, price, description 
        FROM menu_items 
        WHERE category_id = ? AND (is_available = 1 OR is_available IS NULL)
        ORDER BY name
    ''', (category_id,)).fetchall()
    conn.close()
    return jsonify([dict(row) for row in items])

@app.route('/api/customer/order', methods=['POST'])
def create_customer_order():
    data = request.json
    
    table_id = data.get('table_id')
    items = data.get('items', [])
    customer_name = data.get('customer_name', 'Guest')
    customer_phone = data.get('customer_phone', '')
    
    if not items:
        return jsonify({'success': False, 'error': 'No items in cart'})
    
    conn = get_db()
    cursor = conn.cursor()
    
    total = 0
    for item in items:
        price = conn.execute('SELECT price FROM menu_items WHERE id = ?', 
                         (item['menu_item_id'],)).fetchone()
        if price:
            total += price['price'] * item['quantity']
    
    cursor.execute('''
        INSERT INTO orders (table_id, total_amount, customer_name, customer_phone, status, created_at)
        VALUES (?, ?, ?, ?, 'pending', ?)
    ''', (table_id, total, customer_name, customer_phone, datetime.utcnow().isoformat()))
    
    order_id = cursor.lastrowid
    
    for item in items:
        price = conn.execute('SELECT price FROM menu_items WHERE id = ?', 
                         (item['menu_item_id'],)).fetchone()
        unit_price = price['price'] if price else 0
        subtotal = unit_price * item['quantity']
        cursor.execute('''
            INSERT INTO order_items (order_id, menu_item_id, quantity, unit_price, subtotal)
            VALUES (?, ?, ?, ?, ?)
        ''', (order_id, item['menu_item_id'], item['quantity'], unit_price, subtotal))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'order_id': order_id})

@app.route('/api/customer/orders', methods=['GET'])
def get_customer_orders():
    """Get order history for customer (by table or phone)"""
    table_id = request.args.get('table_id')
    phone_id = request.args.get('phone_id')
    
    conn = get_db()
    
    if phone_id:
        # Get orders by phone device ID
        orders = conn.execute('''
            SELECT o.*, t.table_number
            FROM orders o
            LEFT JOIN tables t ON o.table_id = t.id
            WHERE o.phone_id = ?
            ORDER BY o.created_at DESC
            LIMIT 20
        ''', (phone_id,)).fetchall()
    elif table_id:
        # Get orders by table
        orders = conn.execute('''
            SELECT o.*, t.table_number
            FROM orders o
            LEFT JOIN tables t ON o.table_id = t.id
            WHERE o.table_id = ?
            ORDER BY o.created_at DESC
            LIMIT 20
        ''', (table_id,)).fetchall()
    else:
        return jsonify({'success': False, 'error': 'table_id or phone_id required'})
    
    # Get order items for each order
    result = []
    for order in orders:
        order_dict = dict(order)
        items = conn.execute('''
            SELECT oi.*, mi.name as item_name
            FROM order_items oi
            LEFT JOIN menu_items mi ON oi.menu_item_id = mi.id
            WHERE oi.order_id = ?
        ''', (order['id'],)).fetchall()
        order_dict['items'] = [dict(item) for item in items]
        result.append(order_dict)
    
    conn.close()
    return jsonify({'success': True, 'orders': result})

@app.route('/api/customer/order/<int:order_id>', methods=['GET'])
def get_customer_order(order_id):
    """Get specific order details"""
    conn = get_db()
    
    order = conn.execute('SELECT o.*, t.table_number FROM orders o LEFT JOIN tables t ON o.table_id = t.id WHERE o.id = ?', (order_id,)).fetchone()
    
    if not order:
        conn.close()
        return jsonify({'success': False, 'error': 'Order not found'})
    
    items = conn.execute('''
        SELECT oi.*, mi.name as item_name
        FROM order_items oi
        LEFT JOIN menu_items mi ON oi.menu_item_id = mi.id
        WHERE oi.order_id = ?
    ''', (order_id,)).fetchall()
    
    conn.close()
    
    return jsonify({
        'success': True,
        'order': dict(order),
        'items': [dict(item) for item in items]
    })

@app.route('/api/tables/available')
def get_available_tables():
    conn = get_db()
    tables = conn.execute('''
        SELECT t.id, t.table_number, t.capacity,
               COALESCE(ts.status, 'free') as status
        FROM tables t
        LEFT JOIN table_status ts ON t.id = ts.table_id
        ORDER BY t.table_number
    ''').fetchall()
    conn.close()
    return jsonify([dict(row) for row in tables])

@app.route('/api/customer/tables/available')
def get_customer_available_tables():
    conn = get_db()
    tables = conn.execute('''
        SELECT t.id, t.table_number, t.capacity
        FROM tables t
        LEFT JOIN table_status ts ON t.id = ts.table_id
        WHERE t.is_active = 1 AND (ts.status IS NULL OR ts.status = 'free')
        ORDER BY t.table_number
    ''').fetchall()
    conn.close()
    return jsonify([dict(row) for row in tables])

@app.route('/api/customer/tables/<int:table_id>/reserve', methods=['POST'])
def reserve_table_customer(table_id):
    data = request.json
    name = data.get('name')
    phone = data.get('phone')
    
    if not name or not phone:
        return jsonify({'success': False, 'message': 'Name and phone required'})
    
    conn = get_db()
    cursor = conn.cursor()
    
    existing = conn.execute('''
        SELECT status FROM table_status WHERE table_id = ?
    ''', (table_id,)).fetchone()
    
    if existing and existing['status'] != 'free':
        conn.close()
        return jsonify({'success': False, 'message': 'Table not available'})
    
    cursor.execute('''
        INSERT INTO table_status (table_id, status, reservation_name, reservation_phone, occupied_since)
        VALUES (?, 'reserved', ?, ?, datetime('now'))
    ''', (table_id, name, phone))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Table reserved', 'table_id': table_id})

@app.route('/order-confirmation/<int:order_id>')
def order_confirmation(order_id):
    conn = get_db()
    order = conn.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
    
    items = conn.execute('''
        SELECT mi.name, oi.quantity, oi.unit_price, oi.subtotal
        FROM order_items oi
        JOIN menu_items mi ON oi.menu_item_id = mi.id
        WHERE oi.order_id = ?
    ''', (order_id,)).fetchall()
    
    total = sum(item['subtotal'] for item in items)
    conn.close()
    
    return render_template('customer_confirmation.html', order=order, items=items, total=total)

@app.route('/api/order/<int:order_id>/status')
def check_order_status(order_id):
    conn = get_db()
    order = conn.execute('SELECT status FROM orders WHERE id = ?', (order_id,)).fetchone()
    conn.close()
    if order:
        return jsonify({'success': True, 'status': order['status']})
    return jsonify({'success': False, 'error': 'Order not found'})

@app.route('/api/hardware/status')
def hardware_status():
    return jsonify({'hardware_enabled': USE_HARDWARE})


def setup_hardware():
    global hw_interface, hw_running
    
    print("[DEBUG] Setting up hardware...")
    
    if not USE_HARDWARE:
        print("[DEBUG] Hardware disabled in config")
        return
    
    try:
        hw_interface = get_hardware_interface()
        print(f"[DEBUG] Hardware interface created: {hw_interface}")
        
        if hw_interface.init():
            print("[DEBUG] Hardware interface initialized")
            hw_running = True
            
            display_welcome()
            
            thread = threading.Thread(target=keypad_loop, daemon=True)
            thread.start()
            print("[DEBUG] Keypad thread started")
        else:
            print("[DEBUG] Hardware init returned False")
    except Exception as e:
        print(f"[DEBUG] Hardware setup failed: {e}")


def keypad_loop():
    global hw_running
    print("[DEBUG] Keypad loop started")
    while hw_running and hw_interface:
        key = hw_interface.keypad.get_key(timeout=1)
        if key:
            print(f"[DEBUG] Key pressed: {key}")
            process_keypress(key)
        import time
        time.sleep(0.1)


if __name__ == '__main__':
    setup_websocket()
    setup_hardware()
    app.run(host='0.0.0.0', port=5001, debug=True)
