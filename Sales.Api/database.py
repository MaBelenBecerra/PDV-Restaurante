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
    """Schema is managed via pgAdmin SQL script."""
    pass

def init_db():
    """Verify database connection on startup."""
    try:
        conn = get_db()
        conn.close()
        print("Database connection verified successfully.")
    except Exception as e:
        print(f"CRITICAL: Failed to connect to database: {e}")
        print("Please ensure PostgreSQL is running and credentials in .env are correct.")
