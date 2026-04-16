from database.models import Order, OrderItem, MenuItem, Table, TableStatus, DeliveryRecord, Robot, get_session
from datetime import datetime
from services.robot_manager import get_robot_manager

class OrderService:
    def __init__(self, socketio=None):
        self.socketio = socketio
    
    def create_order(self, table_id, items, customer_name=None, customer_phone=None):
        session = get_session()
        try:
            table = session.query(Table).filter(Table.id == table_id).first()
            if not table:
                return None, 'Table not found'
            
            table_status = session.query(TableStatus).filter(TableStatus.table_id == table_id).first()
            if table_status and table_status.status != 'free':
                table_status.status = 'occupied'
                table_status.occupied_since = datetime.utcnow()
            
            total_amount = 0
            order_items = []
            
            for item in items:
                menu_item = session.query(MenuItem).filter(MenuItem.id == item['menu_item_id']).first()
                if menu_item and menu_item.is_available:
                    quantity = item.get('quantity', 1)
                    subtotal = menu_item.price * quantity
                    total_amount += subtotal
                    order_items.append({
                        'menu_item': menu_item,
                        'quantity': quantity,
                        'unit_price': menu_item.price,
                        'subtotal': subtotal
                    })
            
            if not order_items:
                return None, 'No valid items'
            
            order = Order(
                table_id=table_id,
                total_amount=total_amount,
                status='pending',
                customer_name=customer_name,
                customer_phone=customer_phone
            )
            session.add(order)
            session.flush()
            
            for item in order_items:
                order_item = OrderItem(
                    order_id=order.id,
                    menu_item_id=item['menu_item'].id,
                    quantity=item['quantity'],
                    unit_price=item['unit_price'],
                    subtotal=item['subtotal']
                )
                session.add(order_item)
            
            session.commit()
            
            if self.socketio:
                self.socketio.emit('new_order', {
                    'order_id': order.id,
                    'table_id': table_id,
                    'table_number': table.table_number,
                    'total_amount': total_amount,
                    'timestamp': order.created_at.isoformat()
                }, broadcast=True, namespace=None)
            
            return order, None
            
        except Exception as e:
            session.rollback()
            return None, str(e)
        finally:
            session.close()
    
    def get_order(self, order_id):
        session = get_session()
        try:
            order = session.query(Order).filter(Order.id == order_id).first()
            if not order:
                return None
            
            table = session.query(Table).filter(Table.id == order.table_id).first()
            items = session.query(OrderItem).filter(OrderItem.order_id == order_id).all()
            
            items_data = []
            for item in items:
                menu_item = session.query(MenuItem).filter(MenuItem.id == item.menu_item_id).first()
                items_data.append({
                    'id': item.id,
                    'menu_item_id': item.menu_item_id,
                    'name': menu_item.name if menu_item else 'Unknown',
                    'quantity': item.quantity,
                    'unit_price': item.unit_price,
                    'subtotal': item.subtotal
                })
            
            delivery = session.query(DeliveryRecord).filter(DeliveryRecord.order_id == order_id).first()
            robot = None
            if delivery:
                robot = session.query(Robot).filter(Robot.id == delivery.robot_id).first()
            
            return {
                'id': order.id,
                'table_id': order.table_id,
                'table_number': table.table_number if table else None,
                'total_amount': order.total_amount,
                'status': order.status,
                'items': items_data,
                'created_at': order.created_at.isoformat() if order.created_at else None,
                'completed_at': order.completed_at.isoformat() if order.completed_at else None,
                'delivery': {
                    'robot_name': robot.name if robot else None,
                    'status': delivery.status if delivery else None
                } if delivery else None
            }
        finally:
            session.close()
    
    def update_order_status(self, order_id, status):
        session = get_session()
        try:
            order = session.query(Order).filter(Order.id == order_id).first()
            if not order:
                return False, 'Order not found'
            
            order.status = status
            order.updated_at = datetime.utcnow()
            
            if status == 'ready':
                self._assign_robot(order_id)
            
            session.commit()
            
            if self.socketio:
                self.socketio.emit('order_status_update', {
                    'order_id': order_id,
                    'status': status,
                    'timestamp': datetime.utcnow().isoformat()
                }, broadcast=True, namespace=None)
            
            return True, 'Order status updated'
        except Exception as e:
            session.rollback()
            return False, str(e)
        finally:
            session.close()
    
    def _assign_robot(self, order_id):
        session = get_session()
        try:
            robot_manager = get_robot_manager(self.socketio)
            best_robot = robot_manager.get_best_robot(order_id)
            
            if best_robot:
                success, result = robot_manager.assign_order_to_robot(order_id, best_robot.id)
                if success:
                    order = session.query(Order).filter(Order.id == order_id).first()
                    if order:
                        table = session.query(Table).filter(Table.id == order.table_id).first()
                        if table:
                            robot_manager.send_navigation_command(
                                best_robot.id,
                                table.position_x,
                                table.position_y
                            )
        finally:
            session.close()
    
    def get_pending_orders(self):
        session = get_session()
        try:
            orders = session.query(Order).filter(
                Order.status.in_(['pending', 'preparing', 'ready', 'delivering'])
            ).order_by(Order.created_at.asc()).all()
            
            result = []
            for order in orders:
                table = session.query(Table).filter(Table.id == order.table_id).first()
                result.append({
                    'id': order.id,
                    'table_number': table.table_number if table else None,
                    'total_amount': order.total_amount,
                    'status': order.status,
                    'created_at': order.created_at.isoformat() if order.created_at else None
                })
            
            return result
        finally:
            session.close()
    
    def get_today_orders(self):
        session = get_session()
        try:
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            
            orders = session.query(Order).filter(Order.created_at >= today_start).all()
            
            result = []
            for order in orders:
                table = session.query(Table).filter(Table.id == order.table_id).first()
                result.append({
                    'id': order.id,
                    'table_number': table.table_number if table else None,
                    'total_amount': order.total_amount,
                    'status': order.status,
                    'created_at': order.created_at.isoformat() if order.created_at else None
                })
            
            return result
        finally:
            session.close()
    
    def complete_order(self, order_id):
        session = get_session()
        try:
            order = session.query(Order).filter(Order.id == order_id).first()
            if not order:
                return False, 'Order not found'
            
            order.status = 'completed'
            order.completed_at = datetime.utcnow()
            order.updated_at = datetime.utcnow()
            
            table_status = session.query(TableStatus).filter(
                TableStatus.table_id == order.table_id
            ).first()
            if table_status:
                table_status.status = 'cleaning'
            
            session.commit()
            
            if self.socketio:
                self.socketio.emit('order_completed', {
                    'order_id': order_id,
                    'timestamp': datetime.utcnow().isoformat()
                }, broadcast=True, namespace=None)
            
            return True, 'Order completed'
        except Exception as e:
            session.rollback()
            return False, str(e)
        finally:
            session.close()


order_service_instance = None

def get_order_service(socketio=None):
    global order_service_instance
    if order_service_instance is None:
        order_service_instance = OrderService(socketio)
    return order_service_instance