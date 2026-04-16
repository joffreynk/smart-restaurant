from flask_socketio import emit, join_room, leave_room, SocketIO
from flask import request
from database.models import Robot, DeliveryRecord, get_session, TelemetryHistory, Phone, Order, OrderItem, MenuItem, Table, TableStatus
from datetime import datetime
import json
import uuid
import logging

logger = logging.getLogger(__name__)

connected_robots = {}
connected_phones = {}
pending_commands = {}
socketio = None

# Table positions and path mapping for line-following robot
# 3 tables for testing: left (table1), straight (table2), right (table3)
# Dynamic mapping based on table number
TABLE_PATHS = {
    1: {'junction': 'left', 'stop_color': 'red', 'name': 'Table 1', 'description': 'Turn left at junction'},
    2: {'junction': 'straight', 'stop_color': 'red', 'name': 'Table 2', 'description': 'Continue straight'},
    3: {'junction': 'right', 'stop_color': 'red', 'name': 'Table 3', 'description': 'Turn right at junction'},
}

def get_table_path(table_id):
    """Get table path info - dynamic for any table"""
    if table_id in TABLE_PATHS:
        return TABLE_PATHS[table_id]
    # Default: odd=left, even=right
    return {
        'junction': 'left' if table_id % 2 == 1 else 'right',
        'stop_color': 'red',
        'name': f'Table {table_id}',
        'description': f"Turn {'left' if table_id % 2 == 1 else 'right'} at junction"
    }

# Kitchen/Home position (home base)
HOME_POSITION = {'x': 0.0, 'y': 0.0, 'name': 'Kitchen'}

def set_socketio(sio):
    global socketio
    socketio = sio

def log_event(event_type, data, level='INFO'):
    timestamp = datetime.utcnow().isoformat()
    log_data = {'timestamp': timestamp, 'event': event_type, 'data': data}
    
    if level == 'ERROR':
        logger.error(json.dumps(log_data))
    elif level == 'WARNING':
        logger.warning(json.dumps(log_data))
    else:
        logger.info(json.dumps(log_data))

def register_websocket(socketio):
    
    @socketio.on('connect')
    def handle_connect():
        log_event('CLIENT_CONNECT', {'sid': request.sid, 'remote': request.remote_addr})
        emit('connected', {'status': 'connected', 'session_id': request.sid})
    
    @socketio.on('disconnect')
    def handle_disconnect():
        log_event('CLIENT_DISCONNECT', {'sid': request.sid})
        
        for robot_id, sid in list(connected_robots.items()):
            if sid == request.sid:
                session = get_session()
                try:
                    robot = session.query(Robot).filter(Robot.id == robot_id).first()
                    if robot:
                        robot.status = 'offline'
                        session.commit()
                        log_event('ROBOT_OFFLINE', {'robot_id': robot.id, 'name': robot.name})
                finally:
                    session.close()
                del connected_robots[robot_id]
                break
        
        for phone_id, sid in list(connected_phones.items()):
            if sid == request.sid:
                log_event('PHONE_DISCONNECT', {'phone_id': phone_id})
                del connected_phones[phone_id]
                break
    
    @socketio.on('register')
    def handle_register(data):
        device_id = data.get('device_id')
        device_type = data.get('device_type', 'robot')
        
        if device_type == 'robot':
            session = get_session()
            try:
                robot = session.query(Robot).filter(Robot.unique_identifier == device_id).first()
                if robot:
                    robot.status = 'idle'
                    robot.last_seen = datetime.utcnow()
                    session.commit()
                    
                    connected_robots[robot.id] = request.sid
                    join_room(f'robot_{robot.id}')
                    
                    emit('registered', {
                        'success': True,
                        'robot_id': robot.id,
                        'message': 'Robot registered successfully'
                    })
                    
                    emit('state_sync', {
                        'robot_id': robot.id,
                        'status': robot.status,
                        'battery_voltage': robot.battery_voltage,
                        'battery_percentage': robot.battery_percentage,
                        'current_x': robot.current_x,
                        'current_y': robot.current_y,
                        'current_angle': robot.current_angle
                    }, room=f'robot_{robot.id}')
                    
                    print(f'Robot registered: {device_id}')
                else:
                    emit('registered', {'success': False, 'message': 'Robot not found'})
            finally:
                session.close()
    
    @socketio.on('robot_telemetry')
    def handle_telemetry(data):
        device_id = data.get('device_id')
        
        session = get_session()
        try:
            robot = session.query(Robot).filter(Robot.unique_identifier == device_id).first()
            if robot:
                robot.battery_voltage = data.get('battery_voltage', robot.battery_voltage)
                robot.battery_percentage = data.get('battery_percentage', robot.battery_percentage)
                robot.current_x = data.get('current_x', robot.current_x)
                robot.current_y = data.get('current_y', robot.current_y)
                robot.current_angle = data.get('current_angle', robot.current_angle)
                robot.status = data.get('status', robot.status)
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
                
                emit('telemetry_ack', {
                    'success': True,
                    'timestamp': datetime.utcnow().isoformat()
                }, room=request.sid)
                
                socketio.emit('robot_state_update', {
                    'robot_id': robot.id,
                    'robot_name': robot.name,
                    'battery_voltage': robot.battery_voltage,
                    'battery_percentage': robot.battery_percentage,
                    'current_x': robot.current_x,
                    'current_y': robot.current_y,
                    'current_angle': robot.current_angle,
                    'status': robot.status,
                    'last_seen': robot.last_seen.isoformat()
                }, broadcast=True)
        except Exception as e:
            print(f'Telemetry error: {e}')
            session.rollback()
        finally:
            session.close()
    
    @socketio.on('robot_status')
    def handle_status(data):
        device_id = data.get('device_id')
        status = data.get('status')
        
        session = get_session()
        try:
            robot = session.query(Robot).filter(Robot.unique_identifier == device_id).first()
            if robot:
                old_status = robot.status
                robot.status = status
                robot.last_seen = datetime.utcnow()
                session.commit()
                
                emit('status_ack', {
                    'success': True,
                    'old_status': old_status,
                    'new_status': status
                }, room=request.sid)
                
                socketio.emit('robot_status_update', {
                    'robot_id': robot.id,
                    'name': robot.name,
                    'old_status': old_status,
                    'new_status': status,
                    'timestamp': datetime.utcnow().isoformat()
                }, broadcast=True)
        except Exception as e:
            print(f'Status update error: {e}')
        finally:
            session.close()
    
    @socketio.on('delivery_update')
    def handle_delivery_update(data):
        device_id = data.get('device_id')
        delivery_id = data.get('delivery_id')
        status = data.get('status')
        
        session = get_session()
        try:
            robot = session.query(Robot).filter(Robot.unique_identifier == device_id).first()
            if not robot:
                return
            
            delivery = session.query(DeliveryRecord).filter(DeliveryRecord.id == delivery_id).first()
            if delivery:
                delivery.status = status
                if status == 'picked_up':
                    delivery.picked_at = datetime.utcnow()
                    robot.status = 'delivering'
                elif status == 'delivered':
                    delivery.delivered_at = datetime.utcnow()
                elif status == 'completed':
                    delivery.completed_at = datetime.utcnow()
                    robot.status = 'idle'
                elif status == 'customer_no_pickup':
                    delivery.completed_at = datetime.utcnow()
                    robot.status = 'returning'
                
                session.commit()
                
                socketio.emit('delivery_update', {
                    'delivery_id': delivery.id,
                    'order_id': delivery.order_id,
                    'robot_id': robot.id,
                    'status': status,
                    'timestamp': datetime.utcnow().isoformat()
                }, broadcast=True)
                
                socketio.emit('customer_pickup_confirmed', {
                    'delivery_id': delivery.id,
                    'robot_id': robot.id,
                    'status': status,
                    'timestamp': datetime.utcnow().isoformat()
                }, room=f'robot_{robot.id}')
        except Exception as e:
            print(f'Delivery update error: {e}')
        finally:
            session.close()
    
    @socketio.on('command')
    def handle_command(data):
        device_id = data.get('device_id')
        action = data.get('action')
        command_id = data.get('command_id', str(uuid.uuid4()))
        
        session = get_session()
        try:
            robot = session.query(Robot).filter(Robot.unique_identifier == device_id).first()
            if not robot:
                emit('command_response', {
                    'success': False,
                    'command_id': command_id,
                    'message': 'Robot not found'
                }, room=request.sid)
                return
            
            pending_commands[command_id] = {
                'robot_id': robot.id,
                'action': action,
                'timestamp': datetime.utcnow(),
                'data': data
            }
            
            robot.status = data.get('target_status', 'assigned')
            session.commit()
            
            command_data = {
                'command_id': command_id,
                'action': action,
                'target_status': data.get('target_status'),
                'target_x': data.get('target_x'),
                'target_y': data.get('target_y'),
                'path': data.get('path', []),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            emit('robot_command', command_data, room=f'robot_{robot.id}')
            
            emit('command_response', {
                'success': True,
                'command_id': command_id,
                'message': 'Command sent',
                'status': robot.status
            }, room=request.sid)
            
            socketio.emit('command_sent', {
                'robot_id': robot.id,
                'robot_name': robot.name,
                'command_id': command_id,
                'action': action,
                'timestamp': datetime.utcnow().isoformat()
            }, broadcast=True)
            
        except Exception as e:
            print(f'Command error: {e}')
            emit('command_response', {
                'success': False,
                'command_id': command_id,
                'message': str(e)
            }, room=request.sid)
        finally:
            session.close()
    
    @socketio.on('cv_detections')
    def handle_cv_detections(data):
        pass
    
    @socketio.on('navigate_to_table')
    def handle_navigate_to_table(data):
        device_id = data.get('device_id')
        table_id = data.get('table_id')
        
        TABLE_POSITIONS = {
            'table_1': {'real_x': 1.0, 'real_y': 1.0},
            'table_2': {'real_x': 1.0, 'real_y': 3.0},
            'table_3': {'real_x': 3.0, 'real_y': 1.0},
            'table_4': {'real_x': 3.0, 'real_y': 3.0},
            'table_5': {'real_x': 5.0, 'real_y': 2.0},
        }
        
        session = get_session()
        try:
            table_pos = TABLE_POSITIONS.get(table_id)
            if not table_pos:
                emit('navigation_response', {
                    'success': False,
                    'message': f'Table {table_id} not found'
                }, room=request.sid)
                return
            
            robot = session.query(Robot).filter(Robot.unique_identifier == device_id).first()
            if not robot:
                emit('navigation_response', {
                    'success': False,
                    'message': 'Robot not found'
                }, room=request.sid)
                return
            
            path = [
                {'x': robot.current_x, 'y': robot.current_y},
                {'x': table_pos['real_x'], 'y': table_pos['real_y']}
            ]
            
            command_id = str(uuid.uuid4())
            emit('robot_command', {
                'command_id': command_id,
                'action': 'navigate_to_table',
                'target_x': table_pos['real_x'],
                'target_y': table_pos['real_y'],
                'table_id': table_id,
                'path': path
            }, room=f'robot_{robot.id}')
            
            robot.status = 'delivering'
            session.commit()
            
            emit('navigation_response', {
                'success': True,
                'table_id': table_id,
                'target_x': table_pos['real_x'],
                'target_y': table_pos['real_y'],
                'path': path
            }, room=request.sid)
            
        except Exception as e:
            print(f"Navigation error: {e}")
            emit('navigation_response', {
                'success': False,
                'message': str(e)
            }, room=request.sid)
        finally:
            session.close()
    
    @socketio.on('command_ack')
    def handle_command_ack(data):
        command_id = data.get('command_id')
        success = data.get('success', False)
        
        if command_id in pending_commands:
            cmd = pending_commands[command_id]
            robot_id = cmd['robot_id']
            
            session = get_session()
            try:
                robot = session.query(Robot).filter(Robot.id == robot_id).first()
                if robot and success:
                    pass
                elif robot and not success:
                    robot.status = 'error'
                    session.commit()
            finally:
                session.close()
            
            del pending_commands[command_id]
            
            socketio.emit('command_acknowledged', {
                'command_id': command_id,
                'success': success,
                'timestamp': datetime.utcnow().isoformat()
            }, broadcast=True)
    
    @socketio.on('request_state_sync')
    def handle_state_sync(data):
        device_id = data.get('device_id')
        
        session = get_session()
        try:
            robot = session.query(Robot).filter(Robot.unique_identifier == device_id).first()
            if robot:
                emit('state_sync', {
                    'robot_id': robot.id,
                    'status': robot.status,
                    'battery_voltage': robot.battery_voltage,
                    'battery_percentage': robot.battery_percentage,
                    'current_x': robot.current_x,
                    'current_y': robot.current_y,
                    'current_angle': robot.current_angle,
                    'timestamp': datetime.utcnow().isoformat()
                }, room=request.sid)
        finally:
            session.close()
    
    @socketio.on('ping')
    def handle_ping(data):
        emit('pong', {'timestamp': datetime.utcnow().isoformat()}, room=request.sid)
    
    @socketio.on('new_order')
    def handle_new_order(data):
        print(f"New order received from kiosk: {data}")
        
        emit('new_order', {
            'order_id': data.get('order_id'),
            'table_number': data.get('table_number'),
            'total': data.get('total'),
            'items': data.get('items'),
            'timestamp': data.get('timestamp')
        }, broadcast=True)
        
        emit('kitchen_order', {
            'order_id': data.get('order_id'),
            'table_number': data.get('table_number'),
            'items': data.get('items'),
            'timestamp': data.get('timestamp')
        }, broadcast=True)
    
    @socketio.on('phone_register')
    def handle_phone_register(data):
        unique_id = data.get('unique_id')
        log_event('PHONE_REGISTER', {'unique_id': unique_id, 'sid': request.sid})
        
        session = get_session()
        try:
            phone = session.query(Phone).filter(Phone.unique_id == unique_id, Phone.is_active == True).first()
            if phone:
                connected_phones[phone.id] = request.sid
                join_room(f'phone_{phone.id}')
                
                emit('registered', {
                    'success': True,
                    'phone_id': phone.id,
                    'message': 'Phone registered successfully'
                })
                
                log_event('PHONE_REGISTERED', {'phone_id': phone.id, 'unique_id': unique_id})
            else:
                emit('registered', {
                    'success': False,
                    'message': 'Phone not registered. Contact admin.'
                })
                log_event('PHONE_REGISTER_FAILED', {'unique_id': unique_id, 'reason': 'not_registered'}, 'WARNING')
        finally:
            session.close()
    
    @socketio.on('order_submit')
    def handle_order_submit(data):
        phone_id = data.get('phone_id')
        table_id = data.get('table_id')
        items = data.get('items', [])
        
        log_event('ORDER_SUBMIT', {'phone_id': phone_id, 'table_id': table_id, 'items_count': len(items)})
        
        session = get_session()
        try:
            phone = session.query(Phone).filter(Phone.unique_id == phone_id, Phone.is_active == True).first()
            if not phone:
                emit('order_response', {
                    'success': False,
                    'message': 'Phone not registered'
                }, room=request.sid)
                return
            
            table = session.query(Table).filter(Table.id == table_id).first()
            if not table:
                emit('order_response', {
                    'success': False,
                    'message': 'Table not found'
                }, room=request.sid)
                return
            
            total_amount = 0
            for item in items:
                menu_item = session.query(MenuItem).filter(MenuItem.id == item.get('menu_item_id')).first()
                if menu_item:
                    total_amount += menu_item.price * item.get('quantity', 1)
            
            order = Order(
                table_id=table_id,
                phone_id=phone.id,
                total_amount=total_amount,
                status='pending',
                customer_name=phone.customer_name,
                customer_phone=phone.customer_phone
            )
            session.add(order)
            session.flush()
            
            for item in items:
                menu_item = session.query(MenuItem).filter(MenuItem.id == item.get('menu_item_id')).first()
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
            
            # Update table status to occupied
            from database.models import TableStatus
            table_status = session.query(TableStatus).filter(TableStatus.table_id == table_id).first()
            if table_status:
                table_status.status = 'occupied'
                table_status.occupied_since = datetime.utcnow()
            else:
                new_status = TableStatus(table_id=table_id, status='occupied', occupied_since=datetime.utcnow())
                session.add(new_status)
            session.commit()
            
            # Broadcast table update to all devices
            socketio.emit('table_updated', {
                'table_id': table_id,
                'table_number': table.table_number,
                'status': 'occupied'
            }, broadcast=True)
            
            emit('order_response', {
                'success': True,
                'order_id': order.id,
                'message': 'Order submitted, waiting for confirmation'
            }, room=request.sid)
            
            emit('new_order', {
                'order_id': order.id,
                'table_number': table.table_number,
                'total': total_amount,
                'items': items,
                'timestamp': datetime.utcnow().isoformat()
            }, broadcast=True)
            
            emit('kitchen_order', {
                'order_id': order.id,
                'table_number': table.table_number,
                'items': items,
                'timestamp': datetime.utcnow().isoformat()
            }, broadcast=True)
            
            log_event('ORDER_CREATED', {
                'order_id': order.id,
                'phone_id': phone_id,
                'table_number': table.table_number,
                'total_amount': total_amount,
                'items_count': len(items)
            })
            
            print(f'Order {order.id} submitted from phone {phone_id}')
            
        except Exception as e:
            log_event('ORDER_SUBMIT_ERROR', {'phone_id': phone_id, 'error': str(e)}, 'ERROR')
            print(f'Order submit error: {e}')
            emit('order_response', {
                'success': False,
                'message': str(e)
            }, room=request.sid)
            session.rollback()
        finally:
            session.close()
    
    @socketio.on('order_cancel')
    def handle_order_cancel(data):
        phone_id = data.get('phone_id')
        order_id = data.get('order_id')
        
        session = get_session()
        try:
            phone = session.query(Phone).filter(Phone.unique_id == phone_id, Phone.is_active == True).first()
            if not phone:
                return
            
            order = session.query(Order).filter(Order.id == order_id, Order.phone_id == phone.id).first()
            if order and order.status == 'pending':
                order.status = 'cancelled'
                session.commit()
                
                emit('order_cancelled', {
                    'order_id': order_id,
                    'timestamp': datetime.utcnow().isoformat()
                }, broadcast=True)
        finally:
            session.close()
    
    # ================== Robot Waiter Handler ==================
    
    @socketio.on('robot_ready_for_delivery')
    def handle_robot_ready_for_delivery(data):
        """Called when robot connects and is ready to receive delivery commands"""
        robot_id = data.get('robot_id')
        device_id = data.get('device_id')
        
        log_event('ROBOT_READY', {'robot_id': robot_id, 'device_id': device_id})
        
        # Register robot in connected robots
        if robot_id:
            connected_robots[robot_id] = request.sid
            join_room(f'robot_{robot_id}')
    
    @socketio.on('request_delivery')
    def handle_request_delivery(data):
        """Server requests robot to deliver order to a table"""
        robot_id = data.get('robot_id')
        order_id = data.get('order_id')
        table_id = data.get('table_id')
        table_number = data.get('table_number')
        
        session = get_session()
        try:
            # Get table info
            table = session.query(Table).filter(Table.id == table_id).first()
            if not table:
                emit('delivery_response', {
                    'success': False,
                    'message': f'Table {table_id} not found'
                }, room=request.sid)
                return
            
            table_info = get_table_path(table_id)
            
            # Send delivery command to robot
            delivery_command = {
                'command_id': str(uuid.uuid4()),
                'action': 'deliver_order',
                'order_id': order_id,
                'table_id': table_id,
                'table_number': table_number,
                'table_name': table_info['name'],
                'junction_turn': table_info['junction'],  # 'left', 'straight', or 'right' at junction
                'junction_return': 'opposite',  # On return: left↔right, straight stays straight
                'stop_at_red': True,  # Stop when red line detected (table reached)
                'path_type': 'forward',
                'forward_path': f"kitchen → junction → {table_info['junction']} → {table_info['name']}",
                'reverse_path': f"{table_info['name']} → junction → turn {table_info['junction']=='left' and 'right' or table_info['junction']=='right' and 'left' or 'straight'} → kitchen",
                'buzzer_duration': 3,  # Short buzzer for 3 seconds when arriving at kitchen
                'loading_wait': 5,  # Wait 5 seconds for chef to load food
                'customer_pickup_wait': 10,  # Wait 10 seconds for customer to pick up food
                'home_pattern': ['black-white', 'black-white', 'black-white']  # Home detection: black/blue then white twice
            }
            
            # Send to specific robot
            if robot_id and robot_id in connected_robots:
                emit('delivery_command', delivery_command, room=connected_robots[robot_id])
                log_event('DELIVERY_SENT', {'robot_id': robot_id, 'order_id': order_id, 'table': table_number})
            else:
                emit('delivery_command', delivery_command, broadcast=True)
                log_event('DELIVERY_BROADCAST', {'order_id': order_id, 'table': table_number})
            
            # Create delivery record
            delivery = DeliveryRecord(
                order_id=order_id,
                robot_id=robot_id,
                status='assigned'
            )
            session.add(delivery)
            session.commit()
            
            emit('delivery_response', {
                'success': True,
                'order_id': order_id,
                'delivery_id': delivery.id,
                'table_number': table_number,
                'table_name': table_info['name'],
                'instructions': f"Follow line to junction, turn {table_info['junction']}, stop at red line for {table_info['name']}"
            }, room=request.sid)
            
        except Exception as e:
            log_event('DELIVERY_ERROR', {'error': str(e)}, 'ERROR')
            emit('delivery_response', {'success': False, 'message': str(e)}, room=request.sid)
        finally:
            session.close()
    
    @socketio.on('delivery_arrived')
    def handle_delivery_arrived(data):
        """Robot reports it has arrived at the table"""
        robot_id = data.get('robot_id')
        order_id = data.get('order_id')
        table_id = data.get('table_id')
        
        log_event('DELIVERY_ARRIVED', {'robot_id': robot_id, 'order_id': order_id, 'table_id': table_id})
        
        # Broadcast to all clients
        emit('delivery_status', {
            'order_id': order_id,
            'status': 'arrived',
            'table_id': table_id,
            'message': 'Food arrived at table! Please pick up.'
        }, broadcast=True)
        
        # Update delivery record
        session = get_session()
        try:
            delivery = session.query(DeliveryRecord).filter(
                DeliveryRecord.order_id == order_id
            ).first()
            if delivery:
                delivery.status = 'arrived'
                delivery.delivered_at = datetime.utcnow()
                session.commit()
        finally:
            session.close()
    
    @socketio.on('delivery_completed')
    def handle_delivery_completed(data):
        """Robot reports delivery completed (after 20s wait)"""
        robot_id = data.get('robot_id')
        order_id = data.get('order_id')
        
        log_event('DELIVERY_COMPLETED', {'robot_id': robot_id, 'order_id': order_id})
        
        # Send return command to robot
        return_command = {
            'command_id': str(uuid.uuid4()),
            'action': 'return_to_kitchen',
            'order_id': order_id,
            'path_type': 'reverse',
            'junction_turn': 'opposite',  # Turn opposite of forward (left↔right, straight stays straight)
            'follow_same_line': True,  # Follow same line back as forward path
            'home_pattern': ['black-white', 'black-white', 'black-white'],  # Detect home: black/blue then white twice
            'home_position': HOME_POSITION
        }
        
        if robot_id and robot_id in connected_robots:
            emit('return_command', return_command, room=connected_robots[robot_id])
        else:
            emit('return_command', return_command, broadcast=True)
        
        # Update delivery record
        session = get_session()
        try:
            delivery = session.query(DeliveryRecord).filter(
                DeliveryRecord.order_id == order_id
            ).first()
            if delivery:
                delivery.status = 'completed'
                delivery.completed_at = datetime.utcnow()
                session.commit()
            
            # Update order status
            order = session.query(Order).filter(Order.id == order_id).first()
            if order:
                order.status = 'delivering'  # Robot is returning
                session.commit()
        finally:
            session.close()
        
        emit('delivery_status', {
            'order_id': order_id,
            'status': 'returning',
            'message': 'Robot returning to kitchen'
        }, broadcast=True)
    
    @socketio.on('robot_home_arrived')
    def handle_robot_home_arrived(data):
        """Robot reports it has returned to kitchen"""
        robot_id = data.get('robot_id')
        
        log_event('ROBOT_HOME', {'robot_id': robot_id})
        
        # Update robot status to idle
        session = get_session()
        try:
            robot = session.query(Robot).filter(Robot.id == robot_id).first()
            if robot:
                robot.status = 'idle'
                robot.current_x = 0.0
                robot.current_y = 0.0
                session.commit()
        finally:
            session.close()
        
        emit('robot_status_update', {
            'robot_id': robot_id,
            'status': 'idle',
            'message': 'Robot ready for next delivery'
        }, broadcast=True)
    
    @socketio.on('robot_delivery_failed')
    def handle_robot_delivery_failed(data):
        """Robot reports delivery failure"""
        robot_id = data.get('robot_id')
        order_id = data.get('order_id')
        failure_reason = data.get('reason', 'Unknown')
        
        log_event('ROBOT_DELIVERY_FAILED', {'robot_id': robot_id, 'order_id': order_id, 'reason': failure_reason}, 'ERROR')
        
        # Update robot status to error
        session = get_session()
        try:
            robot = session.query(Robot).filter(Robot.id == robot_id).first()
            if robot:
                robot.status = 'error'
                session.commit()
            
            # Update order status
            order = session.query(Order).filter(Order.id == order_id).first()
            if order:
                order.status = 'pending'  # Reset to pending for retry
                session.commit()
        finally:
            session.close()
        
        # Notify manager
        emit('delivery_failed', {
            'robot_id': robot_id,
            'order_id': order_id,
            'reason': failure_reason,
            'message': 'Robot delivery failed. Manual delivery required.'
        }, broadcast=True)
    
    @socketio.on('robot_heartbeat')
    def handle_robot_heartbeat(data):
        """Robot sends heartbeat to indicate it's still connected"""
        robot_id = data.get('robot_id')
        battery_level = data.get('battery', 100)
        
        # Update robot last seen and battery
        session = get_session()
        try:
            robot = session.query(Robot).filter(Robot.id == robot_id).first()
            if robot:
                robot.battery_level = battery_level
                session.commit()
        finally:
            session.close()
    
    @socketio.on('robot_reconnected')
    def handle_robot_reconnected(data):
        """Robot reconnected after network issue"""
        robot_id = data.get('robot_id')
        
        log_event('ROBOT_RECONNECTED', {'robot_id': robot_id})
        
        # Update robot status back to idle if it was delivering
        session = get_session()
        try:
            robot = session.query(Robot).filter(Robot.id == robot_id).first()
            if robot and robot.status in ['error', 'offline']:
                robot.status = 'idle'
                session.commit()
        finally:
            session.close()
        
        emit('robot_status_update', {
            'robot_id': robot_id,
            'status': 'idle',
            'message': 'Robot reconnected and ready'
        }, broadcast=True)
    
    @socketio.on('ultrasonic_alert')
    def handle_ultrasonic_alert(data):
        """Robot ultrasonic sensor detected obstacle"""
        robot_id = data.get('robot_id')
        distance = data.get('distance')
        
        log_event('ULTRASONIC_ALERT', {'robot_id': robot_id, 'distance': distance})
        
        emit('robot_alert', {
            'robot_id': robot_id,
            'alert_type': 'obstacle',
            'distance': distance,
            'message': f'Obstacle detected at {distance}cm'
        }, broadcast=True)
    
    @socketio.on('line_sensor_data')
    def handle_line_sensor_data(data):
        """Robot reports line sensor readings"""
        robot_id = data.get('robot_id')
        left = data.get('left')
        center = data.get('center')
        right = data.get('right')
        
        # Log for debugging
        log_event('LINE_SENSOR', {'robot_id': robot_id, 'left': left, 'center': center, 'right': right})
    
    print('WebSocket handlers registered')

from flask import request