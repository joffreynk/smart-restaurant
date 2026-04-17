-- SQLite Database Schema for Smart Restaurant System
-- Version 1.0
-- Last Updated: 2026-04-04

PRAGMA foreign_keys = ON;

-- Categories table
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Menu Items table
CREATE TABLE IF NOT EXISTS menu_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    price REAL NOT NULL,
    image_url TEXT,
    is_available BOOLEAN DEFAULT 1,
    preparation_time INTEGER DEFAULT 15,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
);

-- Tables table
CREATE TABLE IF NOT EXISTS tables (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_number INTEGER NOT NULL UNIQUE,
    capacity INTEGER DEFAULT 4,
    position_x REAL NOT NULL,
    position_y REAL NOT NULL,
    is_active BOOLEAN DEFAULT 1
);

-- Table Status table
CREATE TABLE IF NOT EXISTS table_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_id INTEGER NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('free', 'occupied', 'reserved', 'cleaning')) DEFAULT 'free',
    occupied_since DATETIME,
    reservation_name TEXT,
    reservation_phone TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (table_id) REFERENCES tables(id) ON DELETE CASCADE
);

-- Phones table
CREATE TABLE IF NOT EXISTS phones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    unique_id TEXT NOT NULL UNIQUE,
    customer_name TEXT,
    customer_phone TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Orders table
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_id INTEGER NOT NULL,
    phone_id INTEGER,
    total_amount REAL NOT NULL,
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'confirmed', 'rejected', 'preparing', 'ready', 'delivering', 'completed', 'cancelled')),
    customer_name TEXT,
    customer_phone TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    confirmed_at DATETIME,
    rejected_at DATETIME,
    rejection_reason TEXT,
    FOREIGN KEY (table_id) REFERENCES tables(id),
    FOREIGN KEY (phone_id) REFERENCES phones(id)
);

-- Order Items junction table
CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    menu_item_id INTEGER NOT NULL,
    quantity INTEGER DEFAULT 1,
    unit_price REAL NOT NULL,
    subtotal REAL NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (menu_item_id) REFERENCES menu_items(id)
);

-- Robots table
CREATE TABLE IF NOT EXISTS robots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    unique_identifier TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    status TEXT DEFAULT 'idle' CHECK(status IN ('idle', 'assigned', 'picking_up', 'delivering', 'serving', 'returning', 'charging', 'error', 'maintenance', 'stopped')),
    battery_voltage REAL DEFAULT 4.2,
    battery_percentage INTEGER DEFAULT 100,
    current_x REAL DEFAULT 0,
    current_y REAL DEFAULT 0,
    current_angle REAL DEFAULT 0,
    current_command TEXT,
    current_action TEXT,
    last_error TEXT,
    last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Delivery Records table
CREATE TABLE IF NOT EXISTS delivery_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    robot_id INTEGER NOT NULL,
    status TEXT DEFAULT 'assigned' CHECK(status IN ('assigned', 'picked_up', 'delivered', 'completed', 'failed', 'customer_no_pickup')),
    assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    picked_at DATETIME,
    delivered_at DATETIME,
    completed_at DATETIME,
    route_data TEXT,
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (robot_id) REFERENCES robots(id)
);

-- Navigation Paths table
CREATE TABLE IF NOT EXISTS navigation_paths (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_location TEXT NOT NULL,
    to_location TEXT NOT NULL,
    path_points TEXT NOT NULL,
    distance REAL NOT NULL,
    estimated_time INTEGER NOT NULL,
    usage_count INTEGER DEFAULT 0,
    last_used DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Robot Telemetry History table
CREATE TABLE IF NOT EXISTS telemetry_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    robot_id INTEGER NOT NULL,
    battery_voltage REAL,
    battery_percentage INTEGER,
    current_x REAL,
    current_y REAL,
    current_angle REAL,
    status TEXT,
    recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (robot_id) REFERENCES robots(id) ON DELETE CASCADE
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_menu_items_category ON menu_items(category_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_created ON orders(created_at);
CREATE INDEX IF NOT EXISTS idx_orders_phone ON orders(phone_id);
CREATE INDEX IF NOT EXISTS idx_phones_unique ON phones(unique_id);
CREATE INDEX IF NOT EXISTS idx_table_status_table ON table_status(table_id);
CREATE INDEX IF NOT EXISTS idx_delivery_records_order ON delivery_records(order_id);
CREATE INDEX IF NOT EXISTS idx_delivery_records_robot ON delivery_records(robot_id);
CREATE INDEX IF NOT EXISTS idx_telemetry_history_robot ON telemetry_history(robot_id);
CREATE INDEX IF NOT EXISTS idx_telemetry_history_time ON telemetry_history(recorded_at);
CREATE INDEX IF NOT EXISTS idx_navigation_paths_locations ON navigation_paths(from_location, to_location);

-- Insert default data
INSERT OR IGNORE INTO categories (name, description, display_order, is_active) VALUES 
    ('Appetizers', 'Start your meal with these delicious starters', 1, 1),
    ('Main Courses', 'Hearty main dishes to satisfy your hunger', 2, 1),
    ('Desserts', 'Sweet treats to end your meal', 3, 1),
    ('Beverages', 'Refreshing drinks', 4, 1);

INSERT OR IGNORE INTO menu_items (category_id, name, description, price, is_available, preparation_time) VALUES 
    (1, 'Bruschetta', 'Toasted bread with fresh tomatoes and basil', 8.99, 1, 10),
    (1, 'Caesar Salad', 'Romaine lettuce with Caesar dressing and croutons', 10.99, 1, 8),
    (1, 'Garlic Bread', 'Crispy bread with garlic butter', 5.99, 1, 5),
    (2, 'Grilled Chicken', 'Juicy grilled chicken with herbs', 15.99, 1, 20),
    (2, 'Pasta Carbonara', 'Creamy pasta with bacon and parmesan', 14.99, 1, 18),
    (2, 'Steak & Fries', '8oz steak with crispy fries', 22.99, 1, 25),
    (2, 'Fish & Chips', 'Beer-battered fish with chips', 16.99, 1, 20),
    (3, 'Chocolate Cake', 'Rich chocolate layered cake', 7.99, 1, 5),
    (3, 'Cheesecake', 'Creamy New York style cheesecake', 7.99, 1, 5),
    (3, 'Ice Cream', 'Three scoops of premium ice cream', 5.99, 1, 3),
    (4, 'Soft Drink', 'Choose from cola, lemon, orange', 2.99, 1, 2),
    (4, 'Coffee', 'Freshly brewed coffee', 3.99, 1, 3),
    (4, 'Tea', 'Selection of herbal teas', 3.49, 1, 3),
    (4, 'Fresh Juice', 'Orange, apple, or mixed berry', 4.99, 1, 5);





INSERT OR IGNORE INTO robots (unique_identifier, name, status) VALUES 
    ('ROBOT-001', 'Waiter Bot Alpha', 'idle'),
    ('ROBOT-002', 'Waiter Bot Beta', 'idle');