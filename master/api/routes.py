from flask import Blueprint, request, jsonify, current_app
from database.models import Category, MenuItem, Table, TableStatus, Order, OrderItem, Robot, DeliveryRecord, NavigationPath, TelemetryHistory, Phone, get_session
from datetime import datetime
import json

api = Blueprint('api', __name__, url_prefix='/api')

# SocketIO instance access - global singleton
_socketio = None

def set_socketio(sio):
    global _socketio
    _socketio = sio

def get_socketio():
    global _socketio
    return _socketio

def success_response(data, message='Success'):
    return jsonify({'success': True, 'message': message, 'data': data})

def error_response(message, code=400):
    return jsonify({'success': False, 'message': message}), code

# ================== Categories API ==================

@api.route('/categories', methods=['GET'])
def get_categories():
    session = get_session()
    try:
        include_all = request.args.get('all', '').lower() == 'true'
        query = session.query(Category)
        
        if not include_all:
            query = query.filter((Category.is_active == True) | (Category.is_active == None))
        
        categories = query.order_by(Category.display_order).all()
        data = [{'id': c.id, 'name': c.name, 'description': c.description, 'display_order': c.display_order, 'is_active': c.is_active} for c in categories]
        return success_response(data)
    finally:
        session.close()

@api.route('/categories/<int:id>', methods=['GET'])
def get_category(id):
    session = get_session()
    try:
        category = session.query(Category).filter(Category.id == id).first()
        if not category:
            return error_response('Category not found', 404)
        data = {'id': category.id, 'name': category.name, 'description': category.description, 'display_order': category.display_order, 'is_active': category.is_active}
        return success_response(data)
    finally:
        session.close()

@api.route('/categories', methods=['POST'])
def create_category():
    session = get_session()
    try:
        data = request.get_json()
        if not data or not data.get('name'):
            return error_response('Name is required')
        
        category = Category(
            name=data['name'],
            description=data.get('description'),
            display_order=data.get('display_order', 0)
        )
        session.add(category)
        session.commit()
        
        return success_response({'id': category.id}, 'Category created')
    except Exception as e:
        session.rollback()
        return error_response(str(e))
    finally:
        session.close()

@api.route('/categories/<int:id>', methods=['PUT'])
def update_category(id):
    session = get_session()
    try:
        category = session.query(Category).filter(Category.id == id).first()
        if not category:
            return error_response('Category not found', 404)
        
        data = request.get_json()
        if data.get('name'):
            category.name = data['name']
        if data.get('description') is not None:
            category.description = data['description']
        if data.get('display_order') is not None:
            category.display_order = data['display_order']
        if data.get('is_active') is not None:
            category.is_active = data['is_active']
        
        session.commit()
        return success_response({'id': category.id}, 'Category updated')
    except Exception as e:
        session.rollback()
        return error_response(str(e))
    finally:
        session.close()

@api.route('/categories/<int:id>', methods=['DELETE'])
def delete_category(id):
    session = get_session()
    try:
        category = session.query(Category).filter(Category.id == id).first()
        if not category:
            return error_response('Category not found', 404)
        
        session.delete(category)
        session.commit()
        
        return success_response(None, 'Category deleted')
    except Exception as e:
        session.rollback()
        return error_response(str(e))
    finally:
        session.close()

# ================== Menu Items API ==================

@api.route('/menu-items', methods=['GET'])
def get_menu_items():
    session = get_session()
    try:
        category_id = request.args.get('category_id')
        include_all = request.args.get('all', '').lower() == 'true'
        query = session.query(MenuItem)
        
        if category_id:
            query = query.filter(MenuItem.category_id == category_id)
        
        if not include_all:
            query = query.filter((MenuItem.is_available == True) | (MenuItem.is_available == None))
        
        items = query.all()
        data = [{
            'id': item.id,
            'category_id': item.category_id,
            'name': item.name,
            'description': item.description,
            'price': item.price,
            'image_url': item.image_url,
            'is_available': item.is_available,
            'preparation_time': item.preparation_time
        } for item in items]
        
        return success_response(data)
    finally:
        session.close()

@api.route('/menu-items/<int:id>', methods=['GET'])
def get_menu_item(id):
    session = get_session()
    try:
        item = session.query(MenuItem).filter(MenuItem.id == id).first()
        if not item:
            return error_response('Menu item not found', 404)
        
        data = {
            'id': item.id,
            'category_id': item.category_id,
            'name': item.name,
            'description': item.description,
            'price': item.price,
            'image_url': item.image_url,
            'is_available': item.is_available,
            'preparation_time': item.preparation_time
        }
        return success_response(data)
    finally:
        session.close()

@api.route('/menu-items', methods=['POST'])
def create_menu_item():
    session = get_session()
    try:
        data = request.get_json()
        if not data or not data.get('name') or not data.get('price') or not data.get('category_id'):
            return error_response('Name, price, and category_id are required')
        
        item = MenuItem(
            category_id=data['category_id'],
            name=data['name'],
            description=data.get('description'),
            price=data['price'],
            image_url=data.get('image_url'),
            preparation_time=data.get('preparation_time', 15)
        )
        session.add(item)
        session.commit()
        
        return success_response({'id': item.id}, 'Menu item created')
    except Exception as e:
        session.rollback()
        return error_response(str(e))
    finally:
        session.close()

@api.route('/menu-items/<int:id>', methods=['PUT'])
def update_menu_item(id):
    session = get_session()
    try:
        item = session.query(MenuItem).filter(MenuItem.id == id).first()
        if not item:
            return error_response('Menu item not found', 404)
        
        data = request.get_json()
        if data.get('name'):
            item.name = data['name']
        if data.get('description') is not None:
            item.description = data['description']
        if data.get('price') is not None:
            item.price = data['price']
        if data.get('category_id') is not None:
            item.category_id = data['category_id']
        if data.get('is_available') is not None:
            item.is_available = data['is_available']
        
        session.commit()
        return success_response({'id': item.id}, 'Menu item updated')
    except Exception as e:
        session.rollback()
        return error_response(str(e))
    finally:
        session.close()

@api.route('/menu-items/<int:id>', methods=['DELETE'])
def delete_menu_item(id):
    session = get_session()
    try:
        item = session.query(MenuItem).filter(MenuItem.id == id).first()
        if not item:
            return error_response('Menu item not found', 404)
        
        session.delete(item)
        session.commit()
        
        return success_response(None, 'Menu item deleted')
    except Exception as e:
        session.rollback()
        return error_response(str(e))
    finally:
        session.close()

@api.route('/menu-items/category/<int:category_id>', methods=['GET'])
def get_menu_items_by_category(category_id):
    session = get_session()
    try:
        category_id = int(category_id)
        include_all = request.args.get('all', '').lower() == 'true'
        query = session.query(MenuItem).filter(MenuItem.category_id == category_id)
        
        if not include_all:
            query = query.filter((MenuItem.is_available == True) | (MenuItem.is_available == None))
        
        items = query.all()
        data = [{
            'id': item.id,
            'name': item.name,
            'description': item.description,
            'price': item.price,
            'is_available': item.is_available,
            'preparation_time': item.preparation_time
        } for item in items]
        
        return success_response(data)
    finally:
        session.close()

# ================== Tables API ==================

@api.route('/tables', methods=['GET'])
def get_tables():
    session = get_session()
    try:
        include_all = request.args.get('all', '').lower() == 'true'
        query = session.query(Table)
        
        if not include_all:
            query = query.filter(Table.is_active == True)
        
        tables = query.all()
        data = []
        for t in tables:
            status = session.query(TableStatus).filter(TableStatus.table_id == t.id).first()
            data.append({
                'id': t.id,
                'table_number': t.table_number,
                'capacity': t.capacity,
                'position_x': t.position_x,
                'position_y': t.position_y,
                'status': status.status if status else 'free',
                'is_active': t.is_active
            })
        
        return success_response(data)
    finally:
        session.close()

@api.route('/tables/<int:id>', methods=['GET'])
def get_table(id):
    session = get_session()
    try:
        table = session.query(Table).filter(Table.id == id).first()
        if not table:
            return error_response('Table not found', 404)
        
        status = session.query(TableStatus).filter(TableStatus.table_id == id).first()
        
        data = {
            'id': table.id,
            'table_number': table.table_number,
            'capacity': table.capacity,
            'position_x': table.position_x,
            'position_y': table.position_y,
            'status': status.status if status else 'free'
        }
        return success_response(data)
    finally:
        session.close()

@api.route('/tables', methods=['POST'])
def create_table():
    session = get_session()
    try:
        data = request.get_json()
        if not data or not data.get('table_number') or not data.get('position_x') or not data.get('position_y'):
            return error_response('table_number, position_x, and position_y are required')
        
        table = Table(
            table_number=data['table_number'],
            capacity=data.get('capacity', 4),
            position_x=data['position_x'],
            position_y=data['position_y']
        )
        session.add(table)
        session.flush()
        
        table_status = TableStatus(table_id=table.id, status='free')
        session.add(table_status)
        session.commit()
        
        return success_response({'id': table.id}, 'Table created')
    except Exception as e:
        session.rollback()
        return error_response(str(e))
    finally:
        session.close()

@api.route('/tables/<int:id>', methods=['PUT'])
def update_table(id):
    session = get_session()
    try:
        table = session.query(Table).filter(Table.id == id).first()
        if not table:
            return error_response('Table not found', 404)
        
        data = request.get_json()
        if data.get('table_number'):
            table.table_number = data['table_number']
        if data.get('capacity') is not None:
            table.capacity = data['capacity']
        if data.get('position_x') is not None:
            table.position_x = data['position_x']
        if data.get('position_y') is not None:
            table.position_y = data['position_y']
        
        session.commit()
        return success_response({'id': table.id}, 'Table updated')
    except Exception as e:
        session.rollback()
        return error_response(str(e))
    finally:
        session.close()

@api.route('/tables/<int:id>', methods=['DELETE'])
def delete_table(id):
    session = get_session()
    try:
        table = session.query(Table).filter(Table.id == id).first()
        if not table:
            return error_response('Table not found', 404)
        
        table.is_active = False
        session.commit()
        
        return success_response(None, 'Table deleted')
    except Exception as e:
        session.rollback()
        return error_response(str(e))
    finally:
        session.close()

@api.route('/tables/<int:id>/status', methods=['PUT'])
def update_table_status(id):
    session = get_session()
    try:
        table = session.query(Table).filter(Table.id == id).first()
        if not table:
            return error_response('Table not found', 404)
        
        data = request.get_json()
        status = data.get('status')
        
        if status not in ['free', 'occupied', 'reserved', 'cleaning']:
            return error_response('Invalid status. Must be: free, occupied, reserved, or cleaning')
        
        table_status = session.query(TableStatus).filter(TableStatus.table_id == id).first()
        if table_status:
            table_status.status = status
        else:
            table_status = TableStatus(table_id=id, status=status)
            session.add(table_status)
        
        session.commit()
        
        return success_response({'id': table.id, 'status': status}, 'Table status updated')
    except Exception as e:
        session.rollback()
        return error_response(str(e))
    finally:
        session.close()

@api.route('/tables/available', methods=['GET'])
def get_available_tables():
    session = get_session()
    try:
        capacity = request.args.get('capacity', type=int)
        query = session.query(Table).join(TableStatus).filter(
            (Table.is_active == True) | (Table.is_active == None),
            TableStatus.status == 'free'
        )
        
        if capacity:
            query = query.filter(Table.capacity >= capacity)
        
        tables = query.all()
        data = [{
            'id': t.id,
            'table_number': t.table_number,
            'capacity': t.capacity,
            'position_x': t.position_x,
            'position_y': t.position_y
        } for t in tables]
        
        return success_response(data)
    finally:
        session.close()

@api.route('/tables/<int:id>/reserve', methods=['POST'])
def reserve_table(id):
    session = get_session()
    try:
        table = session.query(Table).filter(Table.id == id).first()
        if not table:
            return error_response('Table not found', 404)
        
        status = session.query(TableStatus).filter(TableStatus.table_id == id).first()
        if not status:
            return error_response('Table status not found', 404)
        
        if status.status != 'free':
            return error_response('Table is not available')
        
        data = request.get_json()
        status.status = 'reserved'
        status.reservation_name = data.get('name')
        status.reservation_phone = data.get('phone')
        status.occupied_since = datetime.utcnow()
        
        session.commit()
        
        return success_response({'id': table.id, 'status': status.status}, 'Table reserved')
    except Exception as e:
        session.rollback()
        return error_response(str(e))
    finally:
        session.close()

@api.route('/tables/<int:id>/release', methods=['POST'])
def release_table(id):
    session = get_session()
    try:
        status = session.query(TableStatus).filter(TableStatus.table_id == id).first()
        if not status:
            return error_response('Table status not found', 404)
        
        status.status = 'free'
        status.reservation_name = None
        status.reservation_phone = None
        status.occupied_since = None
        
        session.commit()
        
        return success_response({'id': id, 'status': status.status}, 'Table released')
    except Exception as e:
        session.rollback()
        return error_response(str(e))
    finally:
        session.close()

# ================== Orders API ==================

@api.route('/orders', methods=['GET'])
def get_orders():
    session = get_session()
    try:
        status = request.args.get('status')
        query = session.query(Order)
        
        if status:
            query = query.filter(Order.status == status)
        
        orders = query.order_by(Order.created_at.desc()).all()
        
        # Batch fetch related data to avoid N+1 queries
        table_ids = {order.table_id for order in orders}
        order_ids = [order.id for order in orders]
        
        tables = {t.id: t for t in session.query(Table).filter(Table.id.in_(table_ids)).all()} if table_ids else {}
        items_list = session.query(OrderItem).filter(OrderItem.order_id.in_(order_ids)).all() if order_ids else []
        item_ids = {item.menu_item_id for item in items_list}
        menu_items = {mi.id: mi for mi in session.query(MenuItem).filter(MenuItem.id.in_(item_ids)).all()} if item_ids else {}
        
        # Group items by order_id
        items_by_order = {}
        for item in items_list:
            if item.order_id not in items_by_order:
                items_by_order[item.order_id] = []
            mi = menu_items.get(item.menu_item_id)
            items_by_order[item.order_id].append({
                'name': mi.name if mi else 'Unknown',
                'quantity': item.quantity,
                'subtotal': item.subtotal
            })
        
        data = []
        for order in orders:
            table = tables.get(order.table_id)
            order_items = items_by_order.get(order.id, [])
            
            data.append({
                'id': order.id,
                'table_id': order.table_id,
                'table_number': table.table_number if table else None,
                'total_amount': order.total_amount,
                'status': order.status,
                'created_at': order.created_at.isoformat() if order.created_at else None,
                'items': order_items
            })
        
        return success_response(data)
    finally:
        session.close()

@api.route('/orders/<int:id>', methods=['GET'])
def get_order(id):
    session = get_session()
    try:
        order = session.query(Order).filter(Order.id == id).first()
        if not order:
            return error_response('Order not found', 404)
        
        table = session.query(Table).filter(Table.id == order.table_id).first()
        items = session.query(OrderItem).filter(OrderItem.order_id == id).all()
        
        items_data = []
        for item in items:
            menu_item = session.query(MenuItem).filter(MenuItem.id == item.menu_item_id).first()
            items_data.append({
                'menu_item_id': item.menu_item_id,
                'name': menu_item.name if menu_item else None,
                'quantity': item.quantity,
                'unit_price': item.unit_price,
                'subtotal': item.subtotal
            })
        
        data = {
            'id': order.id,
            'table_id': order.table_id,
            'table_number': table.table_number if table else None,
            'total_amount': order.total_amount,
            'status': order.status,
            'items': items_data,
            'created_at': order.created_at.isoformat() if order.created_at else None,
            'completed_at': order.completed_at.isoformat() if order.completed_at else None
        }
        
        return success_response(data)
    finally:
        session.close()

@api.route('/orders', methods=['POST'])
def create_order():
    session = get_session()
    try:
        data = request.get_json()
        if not data or not data.get('table_id') or not data.get('items'):
            return error_response('table_id and items are required')
        
        table = session.query(Table).filter(Table.id == data['table_id']).first()
        if not table:
            return error_response('Table not found', 404)
        
        table_status = session.query(TableStatus).filter(TableStatus.table_id == data['table_id']).first()
        if table_status and table_status.status == 'free':
            table_status.status = 'occupied'
            table_status.occupied_since = datetime.utcnow()
        
        total_amount = 0
        for item in data['items']:
            menu_item = session.query(MenuItem).filter(MenuItem.id == item['menu_item_id']).first()
            if menu_item:
                total_amount += menu_item.price * item.get('quantity', 1)
        
        order = Order(
            table_id=data['table_id'],
            total_amount=total_amount,
            status='pending',
            customer_name=data.get('customer_name'),
            customer_phone=data.get('customer_phone')
        )
        session.add(order)
        session.flush()
        
        for item in data['items']:
            menu_item = session.query(MenuItem).filter(MenuItem.id == item['menu_item_id']).first()
            if menu_item:
                quantity = item.get('quantity', 1)
                unit_price = menu_item.price
                subtotal = unit_price * quantity
                
                order_item = OrderItem(
                    order_id=order.id,
                    menu_item_id=item['menu_item_id'],
                    quantity=quantity,
                    unit_price=unit_price,
                    subtotal=subtotal
                )
                session.add(order_item)
        
        session.commit()
        
        sio = get_socketio()
        if sio:
            order_items = []
            for item in data['items']:
                menu_item = session.query(MenuItem).filter(MenuItem.id == item['menu_item_id']).first()
                order_items.append({
                    'name': menu_item.name if menu_item else 'Unknown',
                    'quantity': item.get('quantity', 1)
                })
            
            sio.emit('new_order', {
                'order_id': order.id,
                'table_number': table.table_number,
                'total': total_amount,
                'items': order_items,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            sio.emit('kitchen_order', {
                'order_id': order.id,
                'table_number': table.table_number,
                'items': order_items,
                'timestamp': datetime.utcnow().isoformat()
            })
        
        return success_response({'id': order.id, 'total_amount': order.total_amount}, 'Order created')
    except Exception as e:
        session.rollback()
        return error_response(str(e))
    finally:
        session.close()

@api.route('/orders/<int:id>', methods=['PUT'])
def update_order(id):
    session = get_session()
    try:
        order = session.query(Order).filter(Order.id == id).first()
        if not order:
            return error_response('Order not found', 404)
        
        data = request.get_json()
        old_status = order.status
        if data.get('status'):
            order.status = data['status']
        
        session.commit()
        
        sio = get_socketio()
        if sio and old_status != order.status:
            sio.emit('order_status_update', {
                'order_id': order.id,
                'old_status': old_status,
                'new_status': order.status,
                'timestamp': datetime.utcnow().isoformat()
            })
        
        return success_response({'id': order.id}, 'Order updated')
    except Exception as e:
        session.rollback()
        return error_response(str(e))
    finally:
        session.close()

@api.route('/orders/<int:id>/complete', methods=['POST'])
def complete_order(id):
    session = get_session()
    try:
        order = session.query(Order).filter(Order.id == id).first()
        if not order:
            return error_response('Order not found', 404)
        
        old_status = order.status
        order.status = 'completed'
        order.completed_at = datetime.utcnow()
        
        table_status = session.query(TableStatus).filter(TableStatus.table_id == order.table_id).first()
        if table_status:
            table_status.status = 'cleaning'
        
        session.commit()
        
        sio = get_socketio()
        if sio:
            sio.emit('order_completed', {
                'order_id': order.id,
                'old_status': old_status,
                'new_status': 'completed',
                'table_id': order.table_id,
                'timestamp': datetime.utcnow().isoformat()
            })
        
        return success_response({'id': order.id, 'status': order.status}, 'Order completed')
    except Exception as e:
        session.rollback()
        return error_response(str(e))
    finally:
        session.close()

@api.route('/orders/active', methods=['GET'])
def get_active_orders():
    session = get_session()
    try:
        orders = session.query(Order).filter(Order.status.in_(['pending', 'preparing', 'ready', 'delivering'])).order_by(Order.created_at.asc()).all()
        data = []
        for order in orders:
            table = session.query(Table).filter(Table.id == order.table_id).first()
            data.append({
                'id': order.id,
                'table_id': order.table_id,
                'table_number': table.table_number if table else None,
                'total_amount': order.total_amount,
                'status': order.status,
                'created_at': order.created_at.isoformat() if order.created_at else None
            })
        
        return success_response(data)
    finally:
        session.close()

# ================== Robots API ==================

@api.route('/robots', methods=['GET'])
def get_robots():
    session = get_session()
    try:
        robots = session.query(Robot).all()
        data = [{
            'id': r.id,
            'unique_identifier': r.unique_identifier,
            'name': r.name,
            'status': r.status,
            'battery_voltage': r.battery_voltage,
            'battery_percentage': r.battery_percentage,
            'current_x': r.current_x,
            'current_y': r.current_y,
            'current_angle': r.current_angle,
            'current_action': r.current_action,
            'current_command': r.current_command,
            'last_error': r.last_error,
            'last_seen': r.last_seen.isoformat() if r.last_seen else None
        } for r in robots]
        
        return success_response(data)
    finally:
        session.close()

@api.route('/robots', methods=['POST'])
def create_robot():
    session = get_session()
    try:
        data = request.get_json()
        if not data or not data.get('unique_identifier') or not data.get('name'):
            return error_response('unique_identifier and name are required')
        
        existing = session.query(Robot).filter(Robot.unique_identifier == data['unique_identifier']).first()
        if existing:
            return error_response('Robot already registered', 400)
        
        robot = Robot(
            unique_identifier=data['unique_identifier'],
            name=data['name'],
            status='idle'
        )
        session.add(robot)
        session.commit()
        
        return success_response({'id': robot.id}, 'Robot created')
    except Exception as e:
        session.rollback()
        return error_response(str(e))
    finally:
        session.close()

@api.route('/robots/<int:id>', methods=['GET'])
def get_robot(id):
    session = get_session()
    try:
        robot = session.query(Robot).filter(Robot.id == id).first()
        if not robot:
            return error_response('Robot not found', 404)
        
        data = {
            'id': robot.id,
            'unique_identifier': robot.unique_identifier,
            'name': robot.name,
            'status': robot.status,
            'battery_voltage': robot.battery_voltage,
            'battery_percentage': robot.battery_percentage,
            'current_x': robot.current_x,
            'current_y': robot.current_y,
            'current_angle': robot.current_angle,
            'current_action': robot.current_action,
            'current_command': robot.current_command,
            'last_error': robot.last_error,
            'last_seen': robot.last_seen.isoformat() if robot.last_seen else None
        }
        
        return success_response(data)
    finally:
        session.close()

@api.route('/robots/unique/<string:uid>', methods=['GET'])
def get_robot_by_uid(uid):
    session = get_session()
    try:
        robot = session.query(Robot).filter(Robot.unique_identifier == uid).first()
        if not robot:
            return error_response('Robot not found', 404)
        
        data = {
            'id': robot.id,
            'unique_identifier': robot.unique_identifier,
            'name': robot.name,
            'status': robot.status,
            'battery_voltage': robot.battery_voltage,
            'battery_percentage': robot.battery_percentage,
            'current_x': robot.current_x,
            'current_y': robot.current_y,
            'current_angle': robot.current_angle,
            'current_action': robot.current_action,
            'current_command': robot.current_command,
            'last_error': robot.last_error,
            'last_seen': robot.last_seen.isoformat() if robot.last_seen else None
        }
        
        return success_response(data)
    finally:
        session.close()

@api.route('/robots/<int:id>/status', methods=['PUT'])
def update_robot_status(id):
    session = get_session()
    try:
        robot = session.query(Robot).filter(Robot.id == id).first()
        if not robot:
            return error_response('Robot not found', 404)
        
        data = request.get_json()
        if data.get('status'):
            robot.status = data['status']
        
        session.commit()
        return success_response({'id': robot.id, 'status': robot.status}, 'Robot status updated')
    except Exception as e:
        session.rollback()
        return error_response(str(e))
    finally:
        session.close()

@api.route('/robots/<int:id>/telemetry', methods=['PUT'])
def update_robot_telemetry(id):
    session = get_session()
    try:
        robot = session.query(Robot).filter(Robot.id == id).first()
        if not robot:
            return error_response('Robot not found', 404)
        
        data = request.get_json()
        if data.get('battery_voltage') is not None:
            robot.battery_voltage = data['battery_voltage']
        if data.get('battery_percentage') is not None:
            robot.battery_percentage = data['battery_percentage']
        if data.get('current_x') is not None:
            robot.current_x = data['current_x']
        if data.get('current_y') is not None:
            robot.current_y = data['current_y']
        if data.get('current_angle') is not None:
            robot.current_angle = data['current_angle']
        if data.get('status') is not None:
            robot.status = data['status']
        if data.get('error') is not None:
            robot.last_error = data['error']
        if data.get('command_completed') is not None:
            if data['command_completed'] and robot.current_command:
                robot.current_command = None
                robot.current_action = None
                if robot.status in ['assigned', 'delivering', 'returning']:
                    robot.status = 'idle'
        if data.get('action') is not None:
            robot.current_action = data['action']
        
        robot.last_seen = datetime.utcnow()
        
        telemetry = TelemetryHistory(
            robot_id=robot.id,
            battery_voltage=robot.battery_voltage,
            battery_percentage=robot.battery_percentage,
            current_x=robot.current_x,
            current_y=robot.current_y,
            current_angle=robot.current_angle,
            status=robot.status
        )
        session.add(telemetry)
        
        session.commit()
        return success_response({'id': robot.id}, 'Robot telemetry updated')
    except Exception as e:
        session.rollback()
        return error_response(str(e))
    finally:
        session.close()

@api.route('/robots/<int:id>/analytics', methods=['GET'])
def get_robot_analytics(id):
    session = get_session()
    try:
        robot = session.query(Robot).filter(Robot.id == id).first()
        if not robot:
            return error_response('Robot not found', 404)
        
        deliveries = session.query(DeliveryRecord).filter(DeliveryRecord.robot_id == id).all()
        
        total_deliveries = len(deliveries)
        completed_deliveries = len([d for d in deliveries if d.status == 'completed'])
        avg_delivery_time = 0
        
        if completed_deliveries > 0:
            total_time = 0
            for d in deliveries:
                if d.delivered_at and d.completed_at:
                    total_time += (d.completed_at - d.assigned_at).total_seconds()
            avg_delivery_time = total_time / completed_deliveries
        
        data = {
            'robot_id': robot.id,
            'total_deliveries': total_deliveries,
            'completed_deliveries': completed_deliveries,
            'average_delivery_time_seconds': avg_delivery_time,
            'current_status': robot.status,
            'battery_percentage': robot.battery_percentage
        }
        
        return success_response(data)
    finally:
        session.close()

@api.route('/robots/<int:id>', methods=['PUT'])
def update_robot(id):
    session = get_session()
    try:
        robot = session.query(Robot).filter(Robot.id == id).first()
        if not robot:
            return error_response('Robot not found', 404)
        
        data = request.get_json()
        if data.get('name'):
            robot.name = data['name']
        if data.get('unique_identifier'):
            robot.unique_identifier = data['unique_identifier']
        if data.get('status'):
            robot.status = data['status']
        if data.get('battery_voltage') is not None:
            robot.battery_voltage = data['battery_voltage']
        if data.get('battery_percentage') is not None:
            robot.battery_percentage = data['battery_percentage']
        if data.get('current_x') is not None:
            robot.current_x = data['current_x']
        if data.get('current_y') is not None:
            robot.current_y = data['current_y']
        if data.get('current_angle') is not None:
            robot.current_angle = data['current_angle']
        
        session.commit()
        
        return success_response({'id': robot.id}, 'Robot updated')
    except Exception as e:
        session.rollback()
        return error_response(str(e))
    finally:
        session.close()

@api.route('/robots/<int:id>', methods=['DELETE'])
def delete_robot(id):
    session = get_session()
    try:
        robot = session.query(Robot).filter(Robot.id == id).first()
        if not robot:
            return error_response('Robot not found', 404)
        
        session.delete(robot)
        session.commit()
        
        return success_response(None, 'Robot deleted')
    except Exception as e:
        session.rollback()
        return error_response(str(e))
    finally:
        session.close()

# ================== Delivery Records API ==================

@api.route('/deliveries', methods=['GET'])
def get_deliveries():
    session = get_session()
    try:
        robot_id = request.args.get('robot_id')
        order_id = request.args.get('order_id')
        
        query = session.query(DeliveryRecord)
        
        if robot_id:
            query = query.filter(DeliveryRecord.robot_id == robot_id)
        if order_id:
            query = query.filter(DeliveryRecord.order_id == order_id)
        
        deliveries = query.all()
        data = []
        for d in deliveries:
            robot = session.query(Robot).filter(Robot.id == d.robot_id).first()
            order = session.query(Order).filter(Order.id == d.order_id).first()
            
            data.append({
                'id': d.id,
                'order_id': d.order_id,
                'robot_id': d.robot_id,
                'robot_name': robot.name if robot else None,
                'order_table': order.table_id if order else None,
                'status': d.status,
                'assigned_at': d.assigned_at.isoformat() if d.assigned_at else None,
                'delivered_at': d.delivered_at.isoformat() if d.delivered_at else None
            })
        
        return success_response(data)
    finally:
        session.close()

@api.route('/deliveries/<int:id>', methods=['GET'])
def get_delivery(id):
    session = get_session()
    try:
        delivery = session.query(DeliveryRecord).filter(DeliveryRecord.id == id).first()
        if not delivery:
            return error_response('Delivery not found', 404)
        
        robot = session.query(Robot).filter(Robot.id == delivery.robot_id).first()
        order = session.query(Order).filter(Order.id == delivery.order_id).first()
        
        data = {
            'id': delivery.id,
            'order_id': delivery.order_id,
            'robot_id': delivery.robot_id,
            'robot_name': robot.name if robot else None,
            'status': delivery.status,
            'assigned_at': delivery.assigned_at.isoformat() if delivery.assigned_at else None,
            'picked_at': delivery.picked_at.isoformat() if delivery.picked_at else None,
            'delivered_at': delivery.delivered_at.isoformat() if delivery.delivered_at else None,
            'completed_at': delivery.completed_at.isoformat() if delivery.completed_at else None
        }
        
        return success_response(data)
    finally:
        session.close()

@api.route('/deliveries/<int:id>', methods=['PUT'])
def update_delivery(id):
    session = get_session()
    try:
        delivery = session.query(DeliveryRecord).filter(DeliveryRecord.id == id).first()
        if not delivery:
            return error_response('Delivery not found', 404)
        
        data = request.get_json()
        if data.get('status'):
            delivery.status = data['status']
            if data['status'] == 'picked_up':
                delivery.picked_at = datetime.utcnow()
            elif data['status'] == 'delivered':
                delivery.delivered_at = datetime.utcnow()
            elif data['status'] == 'completed':
                delivery.completed_at = datetime.utcnow()
        
        session.commit()
        return success_response({'id': delivery.id, 'status': delivery.status}, 'Delivery updated')
    except Exception as e:
        session.rollback()
        return error_response(str(e))
    finally:
        session.close()

@api.route('/deliveries/robot/<int:robot_id>', methods=['GET'])
def get_deliveries_by_robot(robot_id):
    session = get_session()
    try:
        deliveries = session.query(DeliveryRecord).filter(DeliveryRecord.robot_id == robot_id).order_by(DeliveryRecord.assigned_at.desc()).all()
        data = []
        for d in deliveries:
            data.append({
                'id': d.id,
                'order_id': d.order_id,
                'status': d.status,
                'assigned_at': d.assigned_at.isoformat() if d.assigned_at else None
            })
        
        return success_response(data)
    finally:
        session.close()

@api.route('/deliveries/order/<int:order_id>', methods=['GET'])
def get_deliveries_by_order(order_id):
    session = get_session()
    try:
        deliveries = session.query(DeliveryRecord).filter(DeliveryRecord.order_id == order_id).all()
        data = []
        for d in deliveries:
            robot = session.query(Robot).filter(Robot.id == d.robot_id).first()
            data.append({
                'id': d.id,
                'robot_id': d.robot_id,
                'robot_name': robot.name if robot else None,
                'status': d.status,
                'assigned_at': d.assigned_at.isoformat() if d.assigned_at else None
            })
        
        return success_response(data)
    finally:
        session.close()

# ================== Navigation API ==================

@api.route('/navigation/paths', methods=['GET'])
def get_navigation_paths():
    session = get_session()
    try:
        paths = session.query(NavigationPath).all()
        data = [{
            'id': p.id,
            'from_location': p.from_location,
            'to_location': p.to_location,
            'distance': p.distance,
            'estimated_time': p.estimated_time,
            'usage_count': p.usage_count
        } for p in paths]
        
        return success_response(data)
    finally:
        session.close()

@api.route('/navigation/path/<string:from_loc>/<string:to_loc>', methods=['GET'])
def get_path(from_loc, to_loc):
    session = get_session()
    try:
        path = session.query(NavigationPath).filter(
            NavigationPath.from_location == from_loc,
            NavigationPath.to_location == to_loc
        ).first()
        
        if not path:
            return error_response('Path not found', 404)
        
        data = {
            'id': path.id,
            'from_location': path.from_location,
            'to_location': path.to_location,
            'path_points': json.loads(path.path_points),
            'distance': path.distance,
            'estimated_time': path.estimated_time
        }
        
        return success_response(data)
    finally:
        session.close()

@api.route('/navigation/path', methods=['POST'])
def create_path():
    session = get_session()
    try:
        data = request.get_json()
        if not data or not data.get('from_location') or not data.get('to_location') or not data.get('path_points'):
            return error_response('from_location, to_location, and path_points are required')
        
        path = NavigationPath(
            from_location=data['from_location'],
            to_location=data['to_location'],
            path_points=json.dumps(data['path_points']),
            distance=data.get('distance', 0),
            estimated_time=data.get('estimated_time', 0)
        )
        session.add(path)
        session.commit()
        
        return success_response({'id': path.id}, 'Path created')
    except Exception as e:
        session.rollback()
        return error_response(str(e))
    finally:
        session.close()

# ================== Dashboard API ==================

@api.route('/dashboard/stats', methods=['GET'])
def get_dashboard_stats():
    session = get_session()
    try:
        from datetime import datetime, timedelta
        today = datetime.utcnow().date()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())
        
        today_orders = session.query(Order).filter(Order.created_at >= today_start, Order.created_at <= today_end).all()
        today_revenue = sum(o.total_amount for o in today_orders if o.status in ['completed', 'delivering'])
        
        tables = session.query(Table).filter((Table.is_active == True) | (Table.is_active == None)).all()
        free_tables = 0
        for t in tables:
            status = session.query(TableStatus).filter(TableStatus.table_id == t.id).first()
            if status and status.status == 'free':
                free_tables += 1
        
        robots = session.query(Robot).all()
        idle_robots = len([r for r in robots if r.status == 'idle'])
        
        data = {
            'total_orders_today': len(today_orders),
            'revenue_today': today_revenue,
            'total_tables': len(tables),
            'free_tables': free_tables,
            'total_robots': len(robots),
            'idle_robots': idle_robots
        }
        
        return success_response(data)
    finally:
        session.close()

@api.route('/dashboard/orders-today', methods=['GET'])
def get_orders_today():
    session = get_session()
    try:
        from datetime import datetime, timedelta
        today = datetime.utcnow().date()
        today_start = datetime.combine(today, datetime.min.time())
        
        orders = session.query(Order).filter(Order.created_at >= today_start).order_by(Order.created_at.desc()).all()
        data = []
        for order in orders:
            table = session.query(Table).filter(Table.id == order.table_id).first()
            data.append({
                'id': order.id,
                'table_id': order.table_id,
                'table_number': table.table_number if table else None,
                'total_amount': order.total_amount,
                'status': order.status,
                'created_at': order.created_at.isoformat() if order.created_at else None
            })
        
        return success_response(data)
    finally:
        session.close()

@api.route('/dashboard/revenue-today', methods=['GET'])
def get_revenue_today():
    session = get_session()
    try:
        from datetime import datetime, timedelta
        today = datetime.utcnow().date()
        today_start = datetime.combine(today, datetime.min.time())
        
        orders = session.query(Order).filter(
            Order.created_at >= today_start,
            Order.status.in_(['completed', 'delivering'])
        ).all()
        
        revenue_by_category = {}
        for order in orders:
            order_items = session.query(OrderItem).filter(OrderItem.order_id == order.id).all()
            for item in order_items:
                menu_item = session.query(MenuItem).filter(MenuItem.id == item.menu_item_id).first()
                if menu_item:
                    category = session.query(Category).filter(Category.id == menu_item.category_id).first()
                    cat_name = category.name if category else 'Unknown'
                    if cat_name not in revenue_by_category:
                        revenue_by_category[cat_name] = 0
                    revenue_by_category[cat_name] += item.subtotal
        
        data = {
            'total_revenue': sum(o.total_amount for o in orders),
            'by_category': revenue_by_category
        }
        
        return success_response(data)
    finally:
        session.close()

@api.route('/dashboard/robot-stats', methods=['GET'])
def get_dashboard_robot_stats():
    session = get_session()
    try:
        robots = session.query(Robot).all()
        data = []
        for robot in robots:
            data.append({
                'id': robot.id,
                'name': robot.name,
                'status': robot.status,
                'battery_percentage': robot.battery_percentage,
                'current_x': robot.current_x,
                'current_y': robot.current_y,
                'last_seen': robot.last_seen.isoformat() if robot.last_seen else None
            })
        return success_response(data)
    finally:
        session.close()

# ================== Robot Command API ==================

@api.route('/robot/telemetry', methods=['POST'])
def robot_telemetry_http():
    data = request.get_json()
    device_id = data.get('device_id')
    status = data.get('status')
    
    print(f'>>> TELEMETRY from {device_id}: {status}')
    
    session = get_session()
    try:
        robot = session.query(Robot).filter(Robot.unique_identifier == device_id).first()
        if robot:
            robot.status = status
            robot.last_seen = datetime.utcnow()
            session.commit()
            return success_response({'id': robot.id, 'status': status})
        return error_response('Robot not found')
    finally:
        session.close()

@api.route('/robot/<string:uid>/command', methods=['GET'])
def robot_get_command(uid):
    session = get_session()
    try:
        robot = session.query(Robot).filter(Robot.unique_identifier == uid).first()
        if robot and robot.current_action:
            return success_response({'action': robot.current_action})
        return success_response({'action': ''})
    finally:
        session.close()

@api.route('/robots/<int:id>/command', methods=['POST'])
def send_robot_command(id):
    data = request.get_json()
    action = data.get('action')
    
    if not action:
        return error_response('Action is required')
    
    session = get_session()
    try:
        robot = session.query(Robot).filter(Robot.id == id).first()
        if not robot:
            return error_response('Robot not found', 404)
        
        if robot.current_command:
            return error_response(f'Robot already executing command: {robot.current_command}')
        
        command_id = f'cmd_{id}_{int(datetime.utcnow().timestamp())}'
        
        if robot.last_error:
            robot.last_error = None
        
        robot.current_command = command_id
        robot.current_action = action
        robot.status = 'assigned'
        
        sio = get_socketio()
        if sio:
            if action == 'deliver':
                sio.emit('delivery_command', {
                    'command_id': command_id,
                    'table': data.get('table', 'table_1')
                }, room=f'robot_{robot.id}')
            elif action == 'return':
                sio.emit('return_command', {
                    'command_id': command_id
                }, room=f'robot_{robot.id}')
            else:
                sio.emit('robot_command', {
                    'command_id': command_id,
                    'action': action,
                    'delivery_id': data.get('delivery_id')
                }, room=f'robot_{robot.id}')
        
        session.commit()
        
        return success_response({
            'robot_id': id,
            'action': action,
            'command_id': command_id
        }, 'Command sent')
    finally:
        session.close()

@api.route('/robots/<int:id>/go-to-table/<int:table_num>', methods=['POST'])
def robot_go_to_table(id, table_num):
    if table_num not in [1, 2]:
        return error_response('Table must be 1 or 2')
    
    action = f'go_to_table_{table_num}'
    
    session = get_session()
    try:
        robot = session.query(Robot).filter(Robot.id == id).first()
        if not robot:
            return error_response('Robot not found', 404)
        
        if robot.current_command:
            return error_response(f'Robot already executing command: {robot.current_command}')
        
        command_id = f'cmd_{id}_{int(datetime.utcnow().timestamp())}'
        
        if robot.last_error:
            robot.last_error = None
        
        robot.current_command = command_id
        robot.current_action = f'leaving_home_to_table_{table_num}'
        robot.status = 'delivering'
        
        sio = get_socketio()
        if sio:
            sio.emit('delivery_command', {
                'command_id': command_id,
                'table': f'table_{table_num}'
            }, room=f'robot_{robot.id}')
        
        session.commit()
        
        return success_response({
            'robot_id': id,
            'action': action,
            'table': table_num
        }, f'Robot going to table {table_num}')
    finally:
        session.close()

@api.route('/robots/<int:id>/return-kitchen', methods=['POST'])
def robot_return_kitchen(id):
    session = get_session()
    try:
        robot = session.query(Robot).filter(Robot.id == id).first()
        if not robot:
            return error_response('Robot not found', 404)
        
        if robot.current_command:
            return error_response(f'Robot already executing command: {robot.current_command}')
        
        command_id = f'cmd_{id}_{int(datetime.utcnow().timestamp())}'
        
        if robot.last_error:
            robot.last_error = None
        
        robot.current_command = command_id
        robot.current_action = 'returning_home'
        robot.status = 'returning'
        
        sio = get_socketio()
        if sio:
            sio.emit('return_command', {
                'command_id': command_id
            }, room=f'robot_{robot.id}')
        
        session.commit()
        
        return success_response({
            'robot_id': id,
            'action': 'return_to_kitchen'
        }, 'Robot returning to kitchen')
    finally:
        session.close()

@api.route('/robots/<int:id>/stop', methods=['POST'])
def robot_stop(id):
    session = get_session()
    try:
        robot = session.query(Robot).filter(Robot.id == id).first()
        if not robot:
            return error_response('Robot not found', 404)
        
        command_id = f'cmd_{id}_{int(datetime.utcnow().timestamp())}'
        
        robot.current_command = None
        robot.current_action = None
        robot.status = 'stopped'
        
        sio = get_socketio()
        if sio:
            sio.emit('robot_stop', {
                'command_id': command_id
            }, room=f'robot_{robot.id}')
        
        session.commit()
        
        return success_response({
            'robot_id': id,
            'action': 'stop'
        }, 'Robot stopped')
    finally:
        session.close()

# ================== Phones API ==================

@api.route('/phones', methods=['GET'])
def get_phones():
    session = get_session()
    try:
        include_all = request.args.get('all', '').lower() == 'true'
        query = session.query(Phone)
        
        if not include_all:
            query = query.filter((Phone.is_active == True) | (Phone.is_active == None))
        
        phones = query.all()
        data = [{
            'id': p.id,
            'unique_id': p.unique_id,
            'customer_name': p.customer_name,
            'customer_phone': p.customer_phone,
            'is_active': p.is_active,
            'created_at': p.created_at.isoformat() if p.created_at else None
        } for p in phones]
        return success_response(data)
    finally:
        session.close()

@api.route('/devices', methods=['GET'])
def get_devices():
    return get_phones()

@api.route('/devices', methods=['POST'])
def create_device():
    return create_phone()

@api.route('/devices/<int:id>', methods=['DELETE'])
def delete_device(id):
    session = get_session()
    try:
        phone = session.query(Phone).filter(Phone.id == id).first()
        if not phone:
            return error_response('Device not found', 404)
        
        phone.is_active = False
        session.commit()
        
        return success_response(None, 'Device deleted')
    except Exception as e:
        session.rollback()
        return error_response(str(e))
    finally:
        session.close()

@api.route('/phones', methods=['POST'])
def create_phone():
    session = get_session()
    try:
        data = request.get_json()
        if not data or not data.get('unique_id'):
            return error_response('unique_id is required')
        
        existing = session.query(Phone).filter(Phone.unique_id == data['unique_id']).first()
        if existing:
            return error_response('Phone already registered', 400)
        
        phone = Phone(
            unique_id=data['unique_id'],
            customer_name=data.get('customer_name'),
            customer_phone=data.get('customer_phone')
        )
        session.add(phone)
        session.commit()
        
        return success_response({'id': phone.id}, 'Phone registered')
    except Exception as e:
        session.rollback()
        return error_response(str(e))
    finally:
        session.close()

@api.route('/phones/<int:id>', methods=['DELETE'])
def delete_phone(id):
    session = get_session()
    try:
        phone = session.query(Phone).filter(Phone.id == id).first()
        if not phone:
            return error_response('Phone not found', 404)
        
        phone.is_active = False
        session.commit()
        
        return success_response(None, 'Phone removed')
    except Exception as e:
        session.rollback()
        return error_response(str(e))
    finally:
        session.close()

@api.route('/phones/<int:id>', methods=['PUT'])
def update_phone(id):
    session = get_session()
    try:
        phone = session.query(Phone).filter(Phone.id == id).first()
        if not phone:
            return error_response('Phone not found', 404)
        
        data = request.get_json()
        if data.get('customer_name'):
            phone.customer_name = data['customer_name']
        if data.get('customer_phone'):
            phone.customer_phone = data['customer_phone']
        if 'is_active' in data:
            phone.is_active = data['is_active']
        
        session.commit()
        
        return success_response({'id': phone.id}, 'Phone updated')
    except Exception as e:
        session.rollback()
        return error_response(str(e))
    finally:
        session.close()

@api.route('/devices/<int:id>', methods=['PUT'])
def update_device(id):
    return update_phone(id)

# ================== Order Confirmation API ==================

def log_event(event_type, data, level='INFO'):
    from datetime import datetime
    import json
    timestamp = datetime.utcnow().isoformat()
    log_data = {'timestamp': timestamp, 'event': event_type, 'data': data}
    import logging
    logger = logging.getLogger(__name__)
    if level == 'ERROR':
        logger.error(json.dumps(log_data))
    else:
        logger.info(json.dumps(log_data))

@api.route('/orders/<int:id>/confirm', methods=['POST'])
def confirm_order(id):
    session = get_session()
    try:
        order = session.query(Order).filter(Order.id == id).first()
        if not order:
            log_event('ORDER_CONFIRM_FAILED', {'order_id': id, 'reason': 'not_found'}, 'ERROR')
            return error_response('Order not found', 404)
        
        if order.status != 'pending':
            log_event('ORDER_CONFIRM_FAILED', {'order_id': id, 'reason': 'wrong_status', 'current_status': order.status}, 'WARNING')
            return error_response('Order already processed')
        
        order.status = 'confirmed'
        order.confirmed_at = datetime.utcnow()
        session.commit()
        
        log_event('ORDER_CONFIRMED', {'order_id': order.id, 'table_id': order.table_id, 'total_amount': order.total_amount})
        
        sio = get_socketio()
        if sio:
            sio.emit('order_confirmed', {
                'order_id': order.id,
                'table_id': order.table_id,
                'timestamp': datetime.utcnow().isoformat()
            })
        
        return success_response({'id': order.id, 'status': order.status}, 'Order confirmed')
    except Exception as e:
        session.rollback()
        log_event('ORDER_CONFIRM_ERROR', {'order_id': id, 'error': str(e)}, 'ERROR')
        return error_response(str(e))
    finally:
        session.close()

@api.route('/orders/<int:id>/reject', methods=['POST'])
def reject_order(id):
    session = get_session()
    try:
        data = request.get_json()
        order = session.query(Order).filter(Order.id == id).first()
        if not order:
            log_event('ORDER_REJECT_FAILED', {'order_id': id, 'reason': 'not_found'}, 'ERROR')
            return error_response('Order not found', 404)
        
        if order.status != 'pending':
            log_event('ORDER_REJECT_FAILED', {'order_id': id, 'reason': 'wrong_status', 'current_status': order.status}, 'WARNING')
            return error_response('Order already processed')
        
        order.status = 'rejected'
        order.rejected_at = datetime.utcnow()
        order.rejection_reason = data.get('reason', 'Not specified')
        session.commit()
        
        log_event('ORDER_REJECTED', {'order_id': order.id, 'reason': order.rejection_reason})
        
        sio = get_socketio()
        if sio:
            sio.emit('order_rejected', {
                'order_id': order.id,
                'reason': order.rejection_reason,
                'timestamp': datetime.utcnow().isoformat()
            })
        
        return success_response({'id': order.id, 'status': order.status}, 'Order rejected')
    except Exception as e:
        session.rollback()
        log_event('ORDER_REJECT_ERROR', {'order_id': id, 'error': str(e)}, 'ERROR')
        return error_response(str(e))
    finally:
        session.close()

@api.route('/customer/menu/<int:category_id>', methods=['GET'])
def get_customer_menu(category_id):
    session = get_session()
    try:
        items = session.query(MenuItem).filter(
            MenuItem.category_id == category_id,
            (MenuItem.is_available == True) | (MenuItem.is_available == None)
        ).all()
        data = [{
            'id': item.id,
            'name': item.name,
            'description': item.description,
            'price': item.price
        } for item in items]
        return success_response(data)
    finally:
        session.close()

def register_routes(app):
    app.register_blueprint(api)