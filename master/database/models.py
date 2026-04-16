from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, CheckConstraint
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime

Base = declarative_base()

class Category(Base):
    __tablename__ = 'categories'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    menu_items = relationship('MenuItem', back_populates='category', cascade='all, delete-orphan')

class MenuItem(Base):
    __tablename__ = 'menu_items'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    category_id = Column(Integer, ForeignKey('categories.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    price = Column(Float, nullable=False)
    image_url = Column(String(500))
    is_available = Column(Boolean, default=True)
    preparation_time = Column(Integer, default=15)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    category = relationship('Category', back_populates='menu_items')
    order_items = relationship('OrderItem', back_populates='menu_item')

class Table(Base):
    __tablename__ = 'tables'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    table_number = Column(Integer, nullable=False, unique=True)
    capacity = Column(Integer, default=4)
    position_x = Column(Float, nullable=False)
    position_y = Column(Float, nullable=False)
    is_active = Column(Boolean, default=True)
    
    table_status = relationship('TableStatus', back_populates='table', uselist=False, cascade='all, delete-orphan')
    orders = relationship('Order', back_populates='table')

class TableStatus(Base):
    __tablename__ = 'table_status'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    table_id = Column(Integer, ForeignKey('tables.id', ondelete='CASCADE'), nullable=False)
    status = Column(String(20), nullable=False, default='free')
    occupied_since = Column(DateTime)
    reservation_name = Column(String(100))
    reservation_phone = Column(String(20))
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    table = relationship('Table', back_populates='table_status')

class Order(Base):
    __tablename__ = 'orders'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    table_id = Column(Integer, ForeignKey('tables.id'), nullable=False)
    phone_id = Column(Integer, ForeignKey('phones.id'), nullable=True)
    total_amount = Column(Float, nullable=False)
    status = Column(String(20), default='pending')
    customer_name = Column(String(100))
    customer_phone = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)
    confirmed_at = Column(DateTime)
    rejected_at = Column(DateTime)
    rejection_reason = Column(Text)
    
    table = relationship('Table', back_populates='orders')
    phone = relationship('Phone', back_populates='orders')
    order_items = relationship('OrderItem', back_populates='order', cascade='all, delete-orphan')
    delivery_records = relationship('DeliveryRecord', back_populates='order', cascade='all, delete-orphan')

class OrderItem(Base):
    __tablename__ = 'order_items'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey('orders.id', ondelete='CASCADE'), nullable=False)
    menu_item_id = Column(Integer, ForeignKey('menu_items.id'), nullable=False)
    quantity = Column(Integer, default=1)
    unit_price = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)
    
    order = relationship('Order', back_populates='order_items')
    menu_item = relationship('MenuItem', back_populates='order_items')

class Robot(Base):
    __tablename__ = 'robots'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    unique_identifier = Column(String(50), nullable=False, unique=True)
    name = Column(String(100), nullable=False)
    status = Column(String(20), default='idle')
    battery_voltage = Column(Float, default=4.2)
    battery_percentage = Column(Integer, default=100)
    current_x = Column(Float, default=0)
    current_y = Column(Float, default=0)
    current_angle = Column(Float, default=0)
    last_seen = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    delivery_records = relationship('DeliveryRecord', back_populates='robot')
    telemetry_history = relationship('TelemetryHistory', back_populates='robot', cascade='all, delete-orphan')

class DeliveryRecord(Base):
    __tablename__ = 'delivery_records'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    robot_id = Column(Integer, ForeignKey('robots.id'), nullable=False)
    status = Column(String(20), default='assigned')
    assigned_at = Column(DateTime, default=datetime.utcnow)
    picked_at = Column(DateTime)
    delivered_at = Column(DateTime)
    completed_at = Column(DateTime)
    route_data = Column(Text)
    
    order = relationship('Order', back_populates='delivery_records')
    robot = relationship('Robot', back_populates='delivery_records')

class NavigationPath(Base):
    __tablename__ = 'navigation_paths'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    from_location = Column(String(50), nullable=False)
    to_location = Column(String(50), nullable=False)
    path_points = Column(Text, nullable=False)
    distance = Column(Float, nullable=False)
    estimated_time = Column(Integer, nullable=False)
    usage_count = Column(Integer, default=0)
    last_used = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

class TelemetryHistory(Base):
    __tablename__ = 'telemetry_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    robot_id = Column(Integer, ForeignKey('robots.id', ondelete='CASCADE'), nullable=False)
    battery_voltage = Column(Float)
    battery_percentage = Column(Integer)
    current_x = Column(Float)
    current_y = Column(Float)
    current_angle = Column(Float)
    status = Column(String(20))
    recorded_at = Column(DateTime, default=datetime.utcnow)
    
    robot = relationship('Robot', back_populates='telemetry_history')

class Phone(Base):
    __tablename__ = 'phones'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    unique_id = Column(String(100), nullable=False, unique=True)
    customer_name = Column(String(100))
    customer_phone = Column(String(20))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    orders = relationship('Order', back_populates='phone')

engine = None

def get_engine(db_path=None):
    global engine
    if engine is None:
        if db_path is None:
            import os
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(base_dir, 'database', 'restaurant.db')
        engine = create_engine(f'sqlite:///{db_path}', echo=False)
    return engine

def get_session():
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()

def init_db(db_path=None):
    engine = get_engine(db_path)
    Base.metadata.create_all(engine)
    return engine