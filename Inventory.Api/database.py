import sqlite3
import os
import uuid

DATABASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'database', 'restaurante.db'))

def get_db():
    """Create a database connection with Row factory and foreign keys enabled."""
    db = sqlite3.connect(DATABASE_PATH)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys = ON')
    return db

def query(sql, params=None, fetch='all'):
    if params is None:
        params = {}
    
    db = get_db()
    cursor = db.cursor()
    
    try:
        cursor.execute(sql, params)
        if fetch == 'all':
            return cursor.fetchall()
        elif fetch == 'one':
            return cursor.fetchone()
        else:
            return None
    finally:
        db.close()

def execute(sql, params=None):
    if params is None:
        params = {}
    
    db = get_db()
    cursor = db.cursor()
    
    try:
        cursor.execute(sql, params)
        db.commit()
        return cursor.lastrowid
    finally:
        db.close()

def run_migrations():
    """Ensure database schema matches standard API contracts (adds UUID cen and standard code columns)."""
    db = get_db()
    cursor = db.cursor()
    
    try:
        # Drop old triggers to prevent double discounting/increasing of stock in modular mode
        cursor.execute("DROP TRIGGER IF EXISTS trg_descontar_stock")
        cursor.execute("DROP TRIGGER IF EXISTS trg_aumentar_stock")
        db.commit()
        
        # 1. Create table 'empresas' if not exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS empresas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cen TEXT NOT NULL UNIQUE,
                nombre TEXT NOT NULL,
                nit TEXT NOT NULL,
                activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0,1)),
                creado_en TEXT NOT NULL DEFAULT (datetime('now'))
            )
        ''')
        
        # Seed default company if none exists
        cursor.execute("SELECT COUNT(*) as count FROM empresas")
        if cursor.fetchone()['count'] == 0:
            cursor.execute(
                "INSERT INTO empresas (cen, nombre, nit, activo) VALUES (?, ?, ?, ?)",
                ('9f2a4e4e-ac9d-46a4-98ea-412d1c168d12', 'Restaurante El Sabor', '20123456789', 1)
            )
        
        # 2. Schema upgrades definition
        migrations = [
            ('categorias', [('cen', 'TEXT'), ('code', 'TEXT')]),
            ('unidades', [('cen', 'TEXT'), ('code', 'TEXT')]),
            ('productos', [('cen', 'TEXT'), ('code', 'TEXT'), ('station_code', 'TEXT')]),
            ('tickets', [('cen', 'TEXT'), ('code', 'TEXT'), ('table_code', 'TEXT'), ('vendor_cen', 'TEXT')]),
            ('ticket_items', [('cen', 'TEXT')]),
            ('pagos', [('cen', 'TEXT')]),
            ('estaciones', [('cen', 'TEXT'), ('code', 'TEXT')]),
            ('comandas', [('cen', 'TEXT')]),
            ('comanda_items', [('cen', 'TEXT')]),
            ('proveedores', [('cen', 'TEXT'), ('code', 'TEXT')]),
            ('compras', [('cen', 'TEXT'), ('code', 'TEXT')]),
            ('compra_items', [('cen', 'TEXT')]),
        ]
        
        # Execute ALTER TABLE to add missing columns dynamically
        for table, columns in migrations:
            # Check existing columns
            cursor.execute(f"PRAGMA table_info({table})")
            existing_columns = {col['name'].lower() for col in cursor.fetchall()}
            
            for col_name, col_type in columns:
                if col_name.lower() not in existing_columns:
                    print(f"Migrating: Adding column {col_name} ({col_type}) to table {table}")
                    cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")
                    
                    # Create index if it's 'cen' or 'code'
                    if col_name.lower() in ('cen', 'code'):
                        cursor.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS idx_{table}_{col_name} ON {table}({col_name})")
        
        db.commit()
        
        # 3. Populate existing rows with GUIDs (cen) where NULL
        tables_with_cen = [t for t, _ in migrations]
        for table in tables_with_cen:
            cursor.execute(f"SELECT id FROM {table} WHERE cen IS NULL")
            rows = cursor.fetchall()
            for row in rows:
                row_id = row['id']
                new_cen = str(uuid.uuid4())
                cursor.execute(f"UPDATE {table} SET cen = ? WHERE id = ?", (new_cen, row_id))
        
        db.commit()
        
        # 4. Populate standard CEN codes if NULL
        cursor.execute("UPDATE categorias SET code = 'CAT-' || printf('%05d', id) WHERE code IS NULL")
        cursor.execute("UPDATE unidades SET code = 'UNI-' || printf('%05d', id) WHERE code IS NULL")
        cursor.execute("UPDATE productos SET code = 'PRO-' || printf('%05d', id) WHERE code IS NULL")
        cursor.execute("UPDATE tickets SET code = 'TIC-' || printf('%05d', id) WHERE code IS NULL")
        cursor.execute("UPDATE estaciones SET code = 'EST-' || printf('%05d', id) WHERE code IS NULL")
        cursor.execute("UPDATE proveedores SET code = 'SUP-' || printf('%05d', id) WHERE code IS NULL")
        cursor.execute("UPDATE compras SET code = 'ORD-' || printf('%05d', id) WHERE code IS NULL")
        
        # Populate station_code for products
        cursor.execute('''
            UPDATE productos SET station_code = 'BAR' 
            WHERE station_code IS NULL AND categoria_id IN (
                SELECT id FROM categorias 
                WHERE LOWER(nombre) LIKE '%bebida%' 
                   OR LOWER(nombre) LIKE '%cóctel%' 
                   OR LOWER(nombre) LIKE '%coctel%'
            )
        ''')
        cursor.execute("UPDATE productos SET station_code = 'COCINA' WHERE station_code IS NULL")
        
        db.commit()
    except Exception as e:
        print(f"Error during schema migration: {e}")
        db.rollback()
    finally:
        db.close()

def init_db():
    """Initialize database and run migrations."""
    db_existed = os.path.exists(DATABASE_PATH)
    if not db_existed:
        db = get_db()
        cursor = db.cursor()
        
        # Check paths for schema.sql
        schema_paths = [
            os.path.join(os.path.dirname(__file__), '..', 'backend', 'schema.sql'),
            os.path.join(os.path.dirname(__file__), '..', 'database', 'schema.sql'),
            os.path.join(os.path.dirname(__file__), 'schema.sql')
        ]
        schema_path = None
        for path in schema_paths:
            if os.path.exists(path):
                schema_path = path
                break
                
        if schema_path:
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema = f.read()
            cursor.executescript(schema)
            db.commit()
            print(f"Database created and seeded from {schema_path}.")
        db.close()
    
    run_migrations()
    print("Database migrations applied successfully.")
