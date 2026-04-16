import threading
import time
from datetime import datetime, timedelta
from database.models import Robot, Order, Table, TableStatus, DeliveryRecord, get_session, NavigationPath
import json

class RobotManager:
    def __init__(self, socketio=None):
        self.socketio = socketio
        self.robots = {}
        self.order_assignments = {}
        self.lock = threading.Lock()
        self.monitoring = False
        self.monitor_thread = None
        
    def register_robot(self, robot_id, device_id):
        with self.lock:
            self.robots[device_id] = {
                'robot_id': robot_id,
                'device_id': device_id,
                'connected': True,
                'last_update': datetime.utcnow()
            }
    
    def unregister_robot(self, device_id):
        with self.lock:
            if device_id in self.robots:
                del self.robots[device_id]
    
    def get_available_robots(self):
        session = get_session()
        try:
            robots = session.query(Robot).filter(
                Robot.status == 'idle',
                Robot.battery_percentage >= 20
            ).all()
            return [{'id': r.id, 'name': r.name, 'battery_percentage': r.battery_percentage} for r in robots]
        finally:
            session.close()
    
    def get_best_robot(self, order_id):
        session = get_session()
        try:
            robots = session.query(Robot).filter(
                Robot.status == 'idle',
                Robot.battery_percentage >= 20
            ).order_by(Robot.battery_percentage.desc()).all()
            
            if not robots:
                return None
            
            order = session.query(Order).filter(Order.id == order_id).first()
            if not order:
                return None
            
            table = session.query(Table).filter(Table.id == order.table_id).first()
            if not table:
                return None
            
            best_robot = None
            min_distance = float('inf')
            
            for robot in robots:
                distance = ((robot.current_x - table.position_x) ** 2 + 
                          (robot.current_y - table.position_y) ** 2) ** 0.5
                if distance < min_distance:
                    min_distance = distance
                    best_robot = robot
            
            return best_robot
        finally:
            session.close()
    
    def assign_order_to_robot(self, order_id, robot_id):
        session = get_session()
        try:
            robot = session.query(Robot).filter(Robot.id == robot_id).first()
            if not robot or robot.status != 'idle':
                return False, 'Robot not available'
            
            order = session.query(Order).filter(Order.id == order_id).first()
            if not order:
                return False, 'Order not found'
            
            delivery = DeliveryRecord(
                order_id=order_id,
                robot_id=robot_id,
                status='assigned'
            )
            session.add(delivery)
            
            robot.status = 'assigned'
            order.status = 'delivering'
            
            session.commit()
            
            with self.lock:
                self.order_assignments[order_id] = {
                    'robot_id': robot_id,
                    'delivery_id': delivery.id,
                    'assigned_at': datetime.utcnow()
                }
            
            return True, {'delivery_id': delivery.id, 'robot_name': robot.name}
            
        except Exception as e:
            session.rollback()
            return False, str(e)
        finally:
            session.close()
    
    def send_navigation_command(self, robot_id, target_x, target_y):
        session = get_session()
        try:
            robot = session.query(Robot).filter(Robot.id == robot_id).first()
            if not robot:
                return False, 'Robot not found'
            
            path = self._calculate_path(
                robot.current_x, robot.current_y,
                target_x, target_y
            )
            
            if self.socketio:
                self.socketio.emit('command', {
                    'device_id': robot.unique_identifier,
                    'action': 'navigate_to_table',
                    'target_x': target_x,
                    'target_y': target_y,
                    'path': path
                })
            
            return True, {'path': path}
        finally:
            session.close()
    
    def _calculate_path(self, start_x, start_y, end_x, end_y):
        path = []
        steps = 10
        
        for i in range(steps + 1):
            t = i / steps
            x = start_x + (end_x - start_x) * t
            y = start_y + (end_y - start_y) * t
            path.append({'x': round(x, 2), 'y': round(y, 2)})
        
        return path
    
    def start_monitoring(self):
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
    
    def _monitor_loop(self):
        while self.monitoring:
            self._check_robot_health()
            time.sleep(5)
    
    def _check_robot_health(self):
        session = get_session()
        try:
            timeout = datetime.utcnow() - timedelta(seconds=30)
            
            robots = session.query(Robot).all()
            for robot in robots:
                if robot.last_seen and robot.last_seen < timeout:
                    robot.status = 'offline'
                    session.commit()
                    
                    if self.socketio:
                        self.socketio.emit('robot_offline', {
                            'robot_id': robot.id,
                            'name': robot.name,
                            'last_seen': robot.last_seen.isoformat()
                        }, broadcast=True)
        finally:
            session.close()
    
    def get_robot_analytics(self, robot_id):
        session = get_session()
        try:
            robot = session.query(Robot).filter(Robot.id == robot_id).first()
            if not robot:
                return None
            
            deliveries = session.query(DeliveryRecord).filter(
                DeliveryRecord.robot_id == robot_id
            ).all()
            
            completed = [d for d in deliveries if d.status == 'completed']
            avg_time = 0
            if completed:
                total_time = sum(
                    (d.completed_at - d.assigned_at).total_seconds()
                    for d in completed if d.completed_at and d.assigned_at
                )
                avg_time = total_time / len(completed)
            
            return {
                'robot_id': robot_id,
                'name': robot.name,
                'status': robot.status,
                'battery_percentage': robot.battery_percentage,
                'total_deliveries': len(deliveries),
                'completed_deliveries': len(completed),
                'average_delivery_time': avg_time,
                'current_position': {
                    'x': robot.current_x,
                    'y': robot.current_y
                }
            }
        finally:
            session.close()
    
    def update_robot_telemetry(self, device_id, telemetry):
        session = get_session()
        try:
            robot = session.query(Robot).filter(Robot.unique_identifier == device_id).first()
            if robot:
                robot.battery_voltage = telemetry.get('battery_voltage', robot.battery_voltage)
                robot.battery_percentage = telemetry.get('battery_percentage', robot.battery_percentage)
                robot.current_x = telemetry.get('current_x', robot.current_x)
                robot.current_y = telemetry.get('current_y', robot.current_y)
                robot.current_angle = telemetry.get('current_angle', robot.current_angle)
                robot.last_seen = datetime.utcnow()
                session.commit()
                return True
            return False
        finally:
            session.close()
    
    def handle_delivery_completed(self, delivery_id):
        session = get_session()
        try:
            delivery = session.query(DeliveryRecord).filter(DeliveryRecord.id == delivery_id).first()
            if delivery:
                delivery.status = 'completed'
                delivery.completed_at = datetime.utcnow()
                
                robot = session.query(Robot).filter(Robot.id == delivery.robot_id).first()
                if robot:
                    robot.status = 'idle'
                
                order = session.query(Order).filter(Order.id == delivery.order_id).first()
                if order:
                    order.status = 'completed'
                    order.completed_at = datetime.utcnow()
                    
                    table_status = session.query(TableStatus).filter(
                        TableStatus.table_id == order.table_id
                    ).first()
                    if table_status:
                        table_status.status = 'cleaning'
                
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            print(f"Delivery completion error: {e}")
            return False
        finally:
            session.close()


robot_manager_instance = None

def get_robot_manager(socketio=None):
    global robot_manager_instance
    if robot_manager_instance is None:
        robot_manager_instance = RobotManager(socketio)
    return robot_manager_instance