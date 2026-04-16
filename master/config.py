import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'restaurant-secret-key-2026')
    
    # Database
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATABASE_PATH = os.path.join(BASE_DIR, 'database', 'restaurant.db')
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{DATABASE_PATH}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Network
    WEBSOCKET_PORT = 8765
    API_PORT = 5000
    DASHBOARD_PORT = 8080
    
    # Computer Vision
    CV_FPS = 10
    CV_INFERENCE_WIDTH = 320
    CV_INFERENCE_HEIGHT = 240
    CV_MODEL_PATH = os.path.join(BASE_DIR, 'cv_models', 'table_status_model.tflite')
    
    # Robot Configuration
    MAX_BATTERY_DISCHARGE = 3.0
    MIN_BATTERY_THRESHOLD = 20
    ULTRASONIC_THRESHOLD = 0.30
    
    # Navigation
    GRID_SIZE = 0.5
    MAX_SPEED = 0.3
    ACCELERATION = 0.1
    
    # Communication
    WEBSOCKET_HEARTBEAT_INTERVAL = 2
    WEBSOCKET_TIMEOUT = 10
    COMMAND_TIMEOUT = 30
    
    # Customer Interface
    SERIAL_PORT = '/dev/ttyUSB0'
    SERIAL_BAUDRATE = 9600
    
    # Admin Dashboard
    ADMIN_USERNAME = 'admin'
    ADMIN_PASSWORD = 'admin123'

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}