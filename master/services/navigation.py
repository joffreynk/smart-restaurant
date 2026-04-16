import math
import json
from database.models import NavigationPath, Table, get_session
from datetime import datetime

class NavigationService:
    def __init__(self):
        self.grid_size = 0.5
        self.known_locations = {}
        self._init_known_locations()
    
    def _init_known_locations(self):
        self.known_locations = {
            'kitchen': {'x': 0.0, 'y': 0.0},
            'entrance': {'x': 6.0, 'y': 0.0},
            'dock': {'x': 0.5, 'y': 0.5},
            'table_1': {'x': 1.0, 'y': 1.0},
            'table_2': {'x': 1.0, 'y': 3.0},
            'table_3': {'x': 3.0, 'y': 1.0},
            'table_4': {'x': 3.0, 'y': 3.0},
            'table_5': {'x': 5.0, 'y': 2.0},
        }
    
    def get_path(self, from_location, to_location):
        session = get_session()
        try:
            path = session.query(NavigationPath).filter(
                NavigationPath.from_location == from_location,
                NavigationPath.to_location == to_location
            ).first()
            
            if path:
                path.usage_count += 1
                path.last_used = datetime.utcnow()
                session.commit()
                
                return json.loads(path.path_points)
            
            return self._calculate_default_path(from_location, to_location)
        finally:
            session.close()
    
    def _calculate_default_path(self, from_location, to_location):
        from_pos = self.known_locations.get(from_location)
        to_pos = self.known_locations.get(to_location)
        
        if not from_pos or not to_pos:
            return self._straight_line_path(from_pos or {'x': 0, 'y': 0}, to_pos or {'x': 0, 'y': 0})
        
        return self._straight_line_path(from_pos, to_pos)
    
    def _straight_line_path(self, from_pos, to_pos):
        path = []
        dx = to_pos['x'] - from_pos['x']
        dy = to_pos['y'] - from_pos['y']
        distance = math.sqrt(dx ** 2 + dy ** 2)
        
        steps = max(int(distance / self.grid_size), 1)
        
        for i in range(steps + 1):
            t = i / steps
            x = from_pos['x'] + dx * t
            y = from_pos['y'] + dy * t
            path.append({'x': round(x, 2), 'y': round(y, 2)})
        
        return path
    
    def learn_path(self, from_location, to_location, path_points):
        session = get_session()
        try:
            existing = session.query(NavigationPath).filter(
                NavigationPath.from_location == from_location,
                NavigationPath.to_location == to_location
            ).first()
            
            if existing:
                existing.path_points = json.dumps(path_points)
                distance = self._calculate_path_distance(path_points)
                existing.distance = distance
                existing.estimated_time = int(distance / 0.3)
                existing.usage_count += 1
                existing.last_used = datetime.utcnow()
            else:
                distance = self._calculate_path_distance(path_points)
                new_path = NavigationPath(
                    from_location=from_location,
                    to_location=to_location,
                    path_points=json.dumps(path_points),
                    distance=distance,
                    estimated_time=int(distance / 0.3)
                )
                session.add(new_path)
            
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f"Learn path error: {e}")
            return False
        finally:
            session.close()
    
    def _calculate_path_distance(self, path_points):
        if len(path_points) < 2:
            return 0
        
        total = 0
        for i in range(len(path_points) - 1):
            dx = path_points[i + 1]['x'] - path_points[i]['x']
            dy = path_points[i + 1]['y'] - path_points[i]['y']
            total += math.sqrt(dx ** 2 + dy ** 2)
        
        return total
    
    def get_table_position(self, table_number):
        location = f'table_{table_number}'
        return self.known_locations.get(location, {'x': 0, 'y': 0})
    
    def get_kitchen_position(self):
        return self.known_locations.get('kitchen', {'x': 0, 'y': 0})
    
    def get_dock_position(self):
        return self.known_locations.get('dock', {'x': 0.5, 'y': 0.5})
    
    def add_known_location(self, name, x, y):
        self.known_locations[name] = {'x': x, 'y': y}
    
    def get_all_locations(self):
        return self.known_locations.copy()


navigation_service_instance = None

def get_navigation_service():
    global navigation_service_instance
    if navigation_service_instance is None:
        navigation_service_instance = NavigationService()
    return navigation_service_instance