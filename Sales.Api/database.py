import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING")
DB_SEARCH_PATH = os.environ.get("DB_SEARCH_PATH", "ventas,inventario,public")

def get_db():
    """Create a database connection with autocommit enabled and set search path."""
    if DB_CONNECTION_STRING:
        # Parse connection string if it's in Key=Value format (common in .env.example)
        if 'Host=' in DB_CONNECTION_STRING:
            params = {}
            for part in DB_CONNECTION_STRING.split(';'):
                if '=' in part:
                    key, val = part.split('=', 1)
                    key = key.strip().lower()
                    val = val.strip()
                    if key == 'host': params['host'] = val
                    elif key == 'port': params['port'] = val
                    elif key == 'database' or key == 'dbname': params['database'] = val
                    elif key == 'username' or key == 'user': params['user'] = val
                    elif key == 'password': params['password'] = val
            conn = psycopg2.connect(
                options=f"-c search_path={DB_SEARCH_PATH}",
                **params
            )
        else:
            # Assume it's a standard libpq URI
            conn = psycopg2.connect(
                DB_CONNECTION_STRING,
                options=f"-c search_path={DB_SEARCH_PATH}"
            )
    else:
        # Fallback to individual variables if provided (even if not in .env.example, for flexibility)
        conn = psycopg2.connect(
            host=os.environ.get("DB_HOST", "localhost"),
            port=os.environ.get("DB_PORT", "5432"),
            database=os.environ.get("DB_NAME", "pdv_restaurante"),
            user=os.environ.get("DB_USER", "postgres"),
            password=os.environ.get("DB_PASSWORD", "postgres"),
            options=f"-c search_path={DB_SEARCH_PATH}"
        )
    return conn

def query(sql, params=None, fetch='all'):
    if params is None:
        params = {}
    
    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cursor.execute(sql, params)
        if fetch == 'all':
            return cursor.fetchall()
        elif fetch == 'one':
            return cursor.fetchone()
        else:
            return None
    finally:
        cursor.close()
        conn.close()

def execute(sql, params=None):
    if params is None:
        params = {}
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        sql_stripped = sql.strip().upper()
        is_insert = sql_stripped.startswith("INSERT")
        has_returning = "RETURNING" in sql_stripped
        
        if is_insert and not has_returning:
            sql = sql.rstrip('; ') + " RETURNING id"
            cursor.execute(sql, params)
            last_id = cursor.fetchone()[0]
            conn.commit()
            return last_id
        else:
            cursor.execute(sql, params)
            last_id = None
            if has_returning:
                last_id = cursor.fetchone()[0]
            conn.commit()
            return last_id
    finally:
        cursor.close()
        conn.close()

def init_db():
    """Verify database connection on startup with retries."""
    import time
    max_retries = 5
    for i in range(max_retries):
        try:
            conn = get_db()
            conn.close()
            print("Database connection verified successfully.")
            return
        except Exception as e:
            print(f"Waiting for database... (attempt {i+1}/{max_retries}): {e}")
            time.sleep(3)
    
    print("CRITICAL: Failed to connect to database after several attempts.")
    print("Please ensure PostgreSQL is running and credentials in .env are correct.")

