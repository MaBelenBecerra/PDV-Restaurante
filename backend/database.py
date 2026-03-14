import sqlite3
import os

DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'restaurante.db')

def get_db():
    """Create a database connection with Row factory and foreign keys enabled."""
    db = sqlite3.connect(DATABASE_PATH)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys = ON')
    return db

def query(sql, params=None, fetch='all'):
    """
    Execute a query and return results.
    
    Args:
        sql: SQL query string
        params: Tuple or dict of parameters (default: None)
        fetch: 'all', 'one', or 'none' (default: 'all')
    
    Returns:
        For fetch='all': list of Row objects
        For fetch='one': single Row object or None
        For fetch='none': None
    """
    if params is None:
        params = {}
    
    db = get_db()
    cursor = db.cursor()
    
    try:
        if isinstance(params, dict):
            cursor.execute(sql, params)
        else:
            cursor.execute(sql, params)
        
        if fetch == 'all':
            return cursor.fetchall()
        elif fetch == 'one':
            return cursor.fetchone()
        else:  # 'none'
            return None
    finally:
        db.close()

def execute(sql, params=None):
    """
    Execute a write operation (INSERT, UPDATE, DELETE).
    
    Args:
        sql: SQL query string
        params: Tuple or dict of parameters (default: None)
    
    Returns:
        lastrowid for INSERT operations
    """
    if params is None:
        params = {}
    
    db = get_db()
    cursor = db.cursor()
    
    try:
        if isinstance(params, dict):
            cursor.execute(sql, params)
        else:
            cursor.execute(sql, params)
        
        db.commit()
        return cursor.lastrowid
    finally:
        db.close()

def init_db():
    """Initialize the database with schema.sql if it doesn't exist."""
    if not os.path.exists(DATABASE_PATH):
        db = get_db()
        cursor = db.cursor()
        
        schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = f.read()
        
        cursor.executescript(schema)
        db.commit()
        db.close()
