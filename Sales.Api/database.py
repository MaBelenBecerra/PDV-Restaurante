import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "pdv_restaurante")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "postgres")
DB_SEARCH_PATH = os.environ.get("DB_SEARCH_PATH", "public")

def get_db():
    """Create a database connection with autocommit enabled and set search path."""
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
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

def run_migrations():
    """Create sales tables if missing and insert seed data."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Create meseros table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS meseros (
                id SERIAL PRIMARY KEY,
                cen VARCHAR(50) NOT NULL UNIQUE,
                nombre VARCHAR(255) NOT NULL,
                email VARCHAR(255),
                telefono VARCHAR(50),
                activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0,1)),
                creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Seed default waiters
        cursor.execute("""
            INSERT INTO meseros (cen, nombre, email, telefono, activo) VALUES
                ('waiter-cen-guid-1', 'Juan Pérez', 'juan.perez@restaurante.local', '555-0199', 1),
                ('waiter-cen-guid-2', 'María López', 'maria.lopez@restaurante.local', '555-0188', 1)
            ON CONFLICT (cen) DO NOTHING;
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        print("Sales migrations completed successfully.")
    except Exception as e:
        print(f"Error running sales migrations: {e}")

def init_db():
    """Verify database connection on startup and run migrations."""
    try:
        conn = get_db()
        conn.close()
        print("Database connection verified successfully.")
        run_migrations()
    except Exception as e:
        print(f"CRITICAL: Failed to connect to database: {e}")
        print("Please ensure PostgreSQL is running and credentials in .env are correct.")

