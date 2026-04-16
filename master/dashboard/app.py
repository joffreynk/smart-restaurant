from flask import Flask, render_template, jsonify, request, redirect, url_for, session, Blueprint
from database.models import get_session, Category, MenuItem, Table, TableStatus, Order, OrderItem, Robot, DeliveryRecord
from datetime import datetime, timedelta
import json

dashboard = Blueprint('dashboard', __name__, template_folder='templates', static_folder='static')
dashboard.secret_key = 'restaurant-dashboard-secret-2026'

@dashboard.route('/')
def index():
    return render_template('dashboard.html')

@dashboard.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == 'admin' and password == 'admin123':
            session['logged_in'] = True
            return redirect(url_for('dashboard.index'))
        else:
            return render_template('login.html', error='Invalid credentials')
    return render_template('login.html')

@dashboard.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('dashboard.login'))

@dashboard.route('/dashboard')
def main_dashboard():
    if 'logged_in' not in session:
        return redirect(url_for('dashboard.login'))
    return render_template('dashboard.html')

@dashboard.route('/api/dashboard/stats')
def dashboard_stats():
    session = get_session()
    try:
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        orders = session.query(Order).filter(Order.created_at >= today).all()
        today_orders = len(orders)
        today_revenue = sum(o.total_amount for o in orders if o.status in ['completed', 'delivering'])
        
        tables = session.query(Table).filter(Table.is_active == True).all()
        free_tables = 0
        for t in tables:
            status = session.query(TableStatus).filter(TableStatus.table_id == t.id).first()
            if status and status.status == 'free':
                free_tables += 1
        
        robots = session.query(Robot).all()
        active_robots = len([r for r in robots if r.status != 'idle'])
        
        return jsonify({
            'today_orders': today_orders,
            'today_revenue': round(today_revenue, 2),
            'total_tables': len(tables),
            'free_tables': free_tables,
            'total_robots': len(robots),
            'active_robots': active_robots
        })
    finally:
        session.close()

@dashboard.route('/menu')
def menu_management():
    if 'logged_in' not in session:
        return redirect(url_for('dashboard.login'))
    return render_template('menu.html')

@dashboard.route('/api/categories')
def api_categories():
    session = get_session()
    try:
        categories = session.query(Category).order_by(Category.display_order).all()
        return jsonify([{
            'id': c.id,
            'name': c.name,
            'description': c.description,
            'display_order': c.display_order,
            'is_active': c.is_active
        } for c in categories])
    finally:
        session.close()

@dashboard.route('/api/categories', methods=['POST'])
def api_create_category():
    session = get_session()
    try:
        data = request.get_json()
        category = Category(
            name=data['name'],
            description=data.get('description', ''),
            display_order=data.get('display_order', 0)
        )
        session.add(category)
        session.commit()
        return jsonify({'id': category.id, 'success': True})
    except Exception as e:
        session.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        session.close()

@dashboard.route('/api/categories/<int:id>', methods=['PUT'])
def api_update_category(id):
    session = get_session()
    try:
        category = session.query(Category).filter(Category.id == id).first()
        if not category:
            return jsonify({'error': 'Not found'}), 404
        
        data = request.get_json()
        category.name = data.get('name', category.name)
        category.description = data.get('description', category.description)
        category.display_order = data.get('display_order', category.display_order)
        category.is_active = data.get('is_active', category.is_active)
        
        session.commit()
        return jsonify({'success': True})
    except Exception as e:
        session.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        session.close()

@dashboard.route('/api/categories/<int:id>', methods=['DELETE'])
def api_delete_category(id):
    session = get_session()
    try:
        category = session.query(Category).filter(Category.id == id).first()
        if category:
            session.delete(category)
            session.commit()
        return jsonify({'success': True})
    except Exception as e:
        session.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        session.close()

@dashboard.route('/api/menu-items')
def api_menu_items():
    session = get_session()
    try:
        items = session.query(MenuItem).all()
        return jsonify([{
            'id': i.id,
            'category_id': i.category_id,
            'category_name': session.query(Category).filter(Category.id == i.category_id).first().name if session.query(Category).filter(Category.id == i.category_id).first() else '',
            'name': i.name,
            'description': i.description,
            'price': i.price,
            'is_available': i.is_available,
            'preparation_time': i.preparation_time
        } for i in items])
    finally:
        session.close()

@dashboard.route('/api/menu-items', methods=['POST'])
def api_create_menu_item():
    session = get_session()
    try:
        data = request.get_json()
        item = MenuItem(
            category_id=data['category_id'],
            name=data['name'],
            description=data.get('description', ''),
            price=data['price'],
            preparation_time=data.get('preparation_time', 15)
        )
        session.add(item)
        session.commit()
        return jsonify({'id': item.id, 'success': True})
    except Exception as e:
        session.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        session.close()

@dashboard.route('/api/menu-items/<int:id>', methods=['PUT'])
def api_update_menu_item(id):
    session = get_session()
    try:
        item = session.query(MenuItem).filter(MenuItem.id == id).first()
        if not item:
            return jsonify({'error': 'Not found'}), 404
        
        data = request.get_json()
        item.name = data.get('name', item.name)
        item.description = data.get('description', item.description)
        item.price = data.get('price', item.price)
        item.category_id = data.get('category_id', item.category_id)
        item.is_available = data.get('is_available', item.is_available)
        item.preparation_time = data.get('preparation_time', item.preparation_time)
        
        session.commit()
        return jsonify({'success': True})
    except Exception as e:
        session.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        session.close()

@dashboard.route('/api/menu-items/<int:id>', methods=['DELETE'])
def api_delete_menu_item(id):
    session = get_session()
    try:
        item = session.query(MenuItem).filter(MenuItem.id == id).first()
        if item:
            session.delete(item)
            session.commit()
        return jsonify({'success': True})
    except Exception as e:
        session.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        session.close()

@dashboard.route('/orders')
def orders_page():
    if 'logged_in' not in session:
        return redirect(url_for('dashboard.login'))
    return render_template('orders.html')

@dashboard.route('/api/orders')
def api_orders():
    session = get_session()
    try:
        status = request.args.get('status')
        query = session.query(Order)
        if status:
            query = query.filter(Order.status == status)
        
        orders = query.order_by(Order.created_at.desc()).limit(50).all()
        result = []
        for o in orders:
            table = session.query(Table).filter(Table.id == o.table_id).first()
            items = session.query(OrderItem).filter(OrderItem.order_id == o.id).all()
            delivery = session.query(DeliveryRecord).filter(DeliveryRecord.order_id == o.id).first()
            robot = session.query(Robot).filter(Robot.id == delivery.robot_id).first() if delivery else None
            
            result.append({
                'id': o.id,
                'table_number': table.table_number if table else None,
                'total_amount': o.total_amount,
                'status': o.status,
                'created_at': o.created_at.isoformat() if o.created_at else None,
                'completed_at': o.completed_at.isoformat() if o.completed_at else None,
                'items_count': len(items),
                'robot_name': robot.name if robot else None
            })
        return jsonify(result)
    finally:
        session.close()

@dashboard.route('/api/orders/<int:id>', methods=['PUT'])
def api_update_order(id):
    session = get_session()
    try:
        order = session.query(Order).filter(Order.id == id).first()
        if not order:
            return jsonify({'error': 'Not found'}), 404
        
        data = request.get_json()
        old_status = order.status
        new_status = data.get('status', order.status)
        order.status = new_status
        
        if data.get('status') == 'completed':
            order.completed_at = datetime.utcnow()
            
            table_status = session.query(TableStatus).filter(TableStatus.table_id == order.table_id).first()
            if table_status:
                table_status.status = 'cleaning'
        
        session.commit()
        
        # Broadcast order status change to all devices
        from api.webSocket import socketio
        if socketio:
            socketio.emit('order_status_changed', {
                'order_id': order.id,
                'old_status': old_status,
                'new_status': new_status,
                'table_id': order.table_id
            }, broadcast=True)
            
            # If order is ready, notify waiters/robots and request delivery
            if new_status == 'ready':
                # Get table info
                table = session.query(Table).filter(Table.id == order.table_id).first()
                table_number = table.table_number if table else 0
                
                socketio.emit('order_ready', {
                    'order_id': order.id,
                    'table_id': order.table_id,
                    'table_number': table_number,
                    'items': [{'name': oi.menu_item.name, 'quantity': oi.quantity} for oi in order.items]
                }, broadcast=True)
                
                # Find available robot and request delivery
                available_robot = session.query(Robot).filter(Robot.status == 'idle').first()
                if available_robot:
                    socketio.emit('request_delivery', {
                        'robot_id': available_robot.id,
                        'order_id': order.id,
                        'table_id': order.table_id,
                        'table_number': table_number
                    }, broadcast=True)
                    log_event('DELIVERY_REQUESTED', {'robot_id': available_robot.id, 'order_id': order.id, 'table': table_number})
                else:
                    # No robot available - notify manager
                    log_event('NO_ROBOT_AVAILABLE', {'order_id': order.id, 'table': table_number}, 'WARNING')
                    socketio.emit('no_robot_available', {
                        'order_id': order.id,
                        'table_id': order.table_id,
                        'table_number': table_number,
                        'message': 'No robot available for delivery. Manual delivery required.'
                    }, broadcast=True)
        
        return jsonify({'success': True})
    except Exception as e:
        session.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        session.close()

@dashboard.route('/robots')
def robots_page():
    if 'logged_in' not in session:
        return redirect(url_for('dashboard.login'))
    return render_template('robots.html')

@dashboard.route('/api/robots')
def api_robots():
    session = get_session()
    try:
        robots = session.query(Robot).all()
        return jsonify([{
            'id': r.id,
            'unique_identifier': r.unique_identifier,
            'name': r.name,
            'status': r.status,
            'battery_voltage': r.battery_voltage,
            'battery_percentage': r.battery_percentage,
            'current_x': r.current_x,
            'current_y': r.current_y,
            'current_angle': r.current_angle,
            'last_seen': r.last_seen.isoformat() if r.last_seen else None
        } for r in robots])
    finally:
        session.close()

@dashboard.route('/api/robots/<int:id>', methods=['PUT'])
def api_update_robot(id):
    session = get_session()
    try:
        robot = session.query(Robot).filter(Robot.id == id).first()
        if not robot:
            return jsonify({'error': 'Not found'}), 404
        
        data = request.get_json()
        robot.name = data.get('name', robot.name)
        robot.status = data.get('status', robot.status)
        
        session.commit()
        return jsonify({'success': True})
    except Exception as e:
        session.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        session.close()

@dashboard.route('/api/robots/<int:id>/analytics')
def api_robot_analytics(id):
    session = get_session()
    try:
        robot = session.query(Robot).filter(Robot.id == id).first()
        if not robot:
            return jsonify({'error': 'Not found'}), 404
        
        deliveries = session.query(DeliveryRecord).filter(DeliveryRecord.robot_id == id).all()
        completed = [d for d in deliveries if d.status == 'completed']
        
        avg_time = 0
        if completed:
            total = sum((d.completed_at - d.assigned_at).total_seconds() for d in completed if d.completed_at and d.assigned_at)
            avg_time = total / len(completed)
        
        return jsonify({
            'total_deliveries': len(deliveries),
            'completed_deliveries': len(completed),
            'average_delivery_time': round(avg_time, 1)
        })
    finally:
        session.close()

@dashboard.route('/robot-subscription')
def robot_subscription():
    if 'logged_in' not in session:
        return redirect(url_for('dashboard.login'))
    return render_template('robot_subscription.html')

@dashboard.route('/api/robots/register', methods=['POST'])
def api_register_robot():
    session = get_session()
    try:
        data = request.get_json()
        
        existing = session.query(Robot).filter(Robot.unique_identifier == data['unique_identifier']).first()
        if existing:
            return jsonify({'error': 'Robot already registered'}), 400
        
        robot = Robot(
            unique_identifier=data['unique_identifier'],
            name=data['name'],
            status='idle'
        )
        session.add(robot)
        session.commit()
        
        return jsonify({'id': robot.id, 'success': True})
    except Exception as e:
        session.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        session.close()

@dashboard.route('/tables')
def tables_page():
    if 'logged_in' not in session:
        return redirect(url_for('dashboard.login'))
    return render_template('tables.html')

@dashboard.route('/api/tables')
def api_tables():
    session = get_session()
    try:
        tables = session.query(Table).filter(Table.is_active == True).all()
        result = []
        for t in tables:
            status = session.query(TableStatus).filter(TableStatus.table_id == t.id).first()
            result.append({
                'id': t.id,
                'table_number': t.table_number,
                'capacity': t.capacity,
                'position_x': t.position_x,
                'position_y': t.position_y,
                'status': status.status if status else 'free',
                'reservation_name': status.reservation_name if status else None
            })
        return jsonify(result)
    finally:
        session.close()

@dashboard.route('/analytics')
def analytics_page():
    if 'logged_in' not in session:
        return redirect(url_for('dashboard.login'))
    return render_template('analytics.html')

@dashboard.route('/api/analytics/serving-time')
def api_serving_time_analytics():
    session = get_session()
    try:
        deliveries = session.query(DeliveryRecord).filter(DeliveryRecord.status == 'completed').all()
        
        robot_stats = {}
        for d in deliveries:
            if d.completed_at and d.assigned_at:
                duration = (d.completed_at - d.assigned_at).total_seconds()
                robot_name = session.query(Robot).filter(Robot.id == d.robot_id).first().name if session.query(Robot).filter(Robot.id == d.robot_id).first() else 'Unknown'
                
                if robot_name not in robot_stats:
                    robot_stats[robot_name] = {'total': 0, 'count': 0}
                
                robot_stats[robot_name]['total'] += duration
                robot_stats[robot_name]['count'] += 1
        
        result = []
        for name, stats in robot_stats.items():
            avg = stats['total'] / stats['count'] if stats['count'] > 0 else 0
            result.append({
                'robot_name': name,
                'total_deliveries': stats['count'],
                'average_time_seconds': round(avg, 1)
            })
        
        return jsonify(result)
    finally:
        session.close()

@dashboard.route('/api/analytics/orders-by-hour')
def api_orders_by_hour():
    session = get_session()
    try:
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        orders = session.query(Order).filter(Order.created_at >= today).all()
        
        hours = {h: 0 for h in range(8, 23)}
        for o in orders:
            if o.created_at:
                hour = o.created_at.hour
                if 8 <= hour < 23:
                    hours[hour] += 1
        
        result = [{'hour': h, 'orders': c} for h, c in hours.items()]
        return jsonify(result)
    finally:
        session.close()


def create_dashboard():
    return dashboard

if __name__ == '__main__':
    dashboard.run(host='0.0.0.0', port=8080, debug=True)