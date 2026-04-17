import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(24).hex()
    
    # Database
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATABASE_PATH = os.path.join(BASE_DIR, 'database', 'restaurant.db')
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{DATABASE_PATH}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Network - All on port 3000 (Flask-SocketIO unified port)
    WEBSOCKET_PORT = int(os.environ.get('WEBSOCKET_PORT', '3000'))
    API_PORT = int(os.environ.get('API_PORT', '3000'))
    
    # Computer Vision (disabled - model not yet trained)
    # CV_FPS = 10
    # CV_INFERENCE_WIDTH = 320
    # CV_INFERENCE_HEIGHT = 240
    # CV_MODEL_PATH = os.path.join(BASE_DIR, 'cv_models', 'table_status_model.tflite')
    
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
    
    # Customer Interface (not used in web-based mode)
    # Cross-platform default serial port
    if os.name == 'nt':
        DEFAULT_SERIAL_PORT = 'COM3'
    else:
        DEFAULT_SERIAL_PORT = '/dev/ttyUSB0'
    SERIAL_PORT = os.environ.get('SERIAL_PORT', DEFAULT_SERIAL_PORT)
    SERIAL_BAUDRATE = 9600
    
    # Admin Dashboard
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'changeme')

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}