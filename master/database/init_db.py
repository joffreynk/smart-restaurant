import sqlite3
import os
from pathlib import Path

def get_db_path():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_dir = os.path.join(base_dir, 'database')
    os.makedirs(db_dir, exist_ok=True)
    return os.path.join(db_dir, 'restaurant.db')

def init_database():
    db_path = get_db_path()
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    
    if not os.path.exists(schema_path):
        print(f"Error: Schema file not found at {schema_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    with open(schema_path, 'r') as f:
        schema_sql = f.read()
        cursor.executescript(schema_sql)
    
    conn.commit()
    conn.close()
    
    print(f"Database initialized at {db_path}")
    return True

def get_connection():
    return sqlite3.connect(get_db_path())

if __name__ == '__main__':
    init_database()