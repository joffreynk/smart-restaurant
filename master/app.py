from flask import Flask, send_from_directory
from flask_socketio import SocketIO
from database.models import init_db
from database.init_db import init_database
import os
import config
import logging
from datetime import datetime
import socket

socketio = None
logger = None

LOG_FILE = os.path.join(os.path.dirname(__file__), 'logs', f'restaurant_{datetime.now().strftime("%Y%m%d")}.log')

def setup_logging():
    os.makedirs(os.path.join(os.path.dirname(__file__), 'logs'), exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# mDNS advertisement for local network hostname resolution
def get_local_ip():
    """Get the local IP address of the machine (not 127.0.0.1)."""
    try:
        # Connect to a public DNS to force selection of the active interface
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        # Use Google's public DNS as a target (doesn't actually send data)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        # Fallback: try to get hostname-based IP
        try:
            hostname = socket.gethostname()
            return socket.gethostbyname(hostname)
        except:
            return '127.0.0.1'

def advertise_mdns(hostname='smart-restaurant', port=3000):
    """Advertise the Flask server via mDNS/Bonjour."""
    try:
        import zeroconf
        from zeroconf import ServiceInfo
        
        local_ip = get_local_ip()
        ip_addresses = [socket.inet_aton(local_ip)]
        
        desc = {'version': '1.0', 'service': 'smart-restaurant-api'}
        
        info = ServiceInfo(
            "_http._tcp.local.",
            f"{hostname}._http._tcp.local.",
            addresses=ip_addresses,
            port=port,
            properties=desc,
            server=f"{hostname}.local."
        )
        
        zc = zeroconf.Zeroconf()
        zc.register_service(info)
        logger.info(f"mDNS advertised as {hostname}.local (IP: {local_ip}) on port {port}")
        return zc
    except Exception as e:
        logger.warning(f"mDNS advertisement not available: {e}")
        return None

def create_app(config_name='default'):
    global socketio, logger
    app = Flask(__name__)
    
    cfg = config.config.get(config_name, config.DevelopmentConfig)
    app.config.from_object(cfg)
    
    socketio = SocketIO(app, cors_allowed_origins='*', ping_interval=60, ping_timeout=60)
    
    db_path = app.config.get('DATABASE_PATH')
    
    if not os.path.exists(db_path):
        logger.info('Creating database with seed data...')
        init_database()
    else:
        init_db(db_path)
    
    logger.info('=' * 50)
    logger.info('Restaurant System Starting')
    logger.info(f'Database: {db_path}')
    
    # mDNS advertisement starts after we get the actual IP
    zeroconf_instance = None
    
    with app.app_context():
        from api.routes import register_routes, set_socketio
        register_routes(app)
        set_socketio(socketio)
        
        from api.webSocket import register_websocket
        register_websocket(socketio)
        
        from dashboard.app import create_dashboard
        dashboard = create_dashboard()
        
        app.register_blueprint(dashboard, url_prefix='/dashboard')
    
    @app.route('/health')
    def health():
        return {'status': 'healthy', 'service': 'smart-restaurant-master'}
    
    @app.route('/')
    def index():
        return {'message': 'Smart Restaurant API', 'endpoints': ['/health', '/api/tables', '/api/orders', '/dashboard', '/phone']}
    
    @app.route('/menu')
    def menu():
        return send_from_directory(os.path.join(os.path.dirname(__file__), 'dashboard', 'templates'), 'menu.html')
    
    @app.route('/orders')
    def orders():
        return send_from_directory(os.path.join(os.path.dirname(__file__), 'dashboard', 'templates'), 'orders.html')
    
    @app.route('/tables')
    def tables():
        return send_from_directory(os.path.join(os.path.dirname(__file__), 'dashboard', 'templates'), 'tables.html')
    
    @app.route('/robots')
    def robots():
        return send_from_directory(os.path.join(os.path.dirname(__file__), 'dashboard', 'templates'), 'robots.html')
    
    @app.route('/robot-subscription')
    def robot_subscription():
        return send_from_directory(os.path.join(os.path.dirname(__file__), 'dashboard', 'templates'), 'robot_subscription.html')
    
    @app.route('/analytics')
    def analytics():
        return send_from_directory(os.path.join(os.path.dirname(__file__), 'dashboard', 'templates'), 'analytics.html')
    
    @app.route('/devices')
    def devices():
        return send_from_directory(os.path.join(os.path.dirname(__file__), 'dashboard', 'templates'), 'devices.html')
    
    @app.route('/order')
    def order_page():
        return send_from_directory(os.path.join(os.path.dirname(__file__), 'dashboard', 'templates'), 'customer_order.html')
    
    @app.route('/phone')
    def phone_client():
        return send_from_directory(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'phone'), 'index.html')
    
    logger.info('Application created successfully')
    
    # Store mdns instance on app for later cleanup
    app.zeroconf = None
    
    return app, socketio

if __name__ == '__main__':
    logger.info('Starting Restaurant Master Server')
    app, socketio = create_app('development')
    
    # Start mDNS advertisement
    zc = advertise_mdns('smart-restaurant', 3000)
    if zc:
        app.zeroconf = zc
    
    try:
        socketio.run(app, host='0.0.0.0', port=3000, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        logger.info('Shutting down...')
    finally:
        if hasattr(app, 'zeroconf') and app.zeroconf:
            app.zeroconf.close()
            logger.info('mDNS stopped')