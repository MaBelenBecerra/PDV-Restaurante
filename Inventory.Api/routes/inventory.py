from flask import Blueprint, request, jsonify, Response
import uuid
import datetime
import queue
import threading
import json
from database import query, execute

bp = Blueprint('inventory', __name__)

restock_lock = threading.Lock()
restock_subscribers = []  # List of dicts: {"company_cen": str, "queue": queue.Queue}

def broadcast_restock(company_cen, product_cen, product_code, product_name, quantity, new_stock, warehouse_cen):
    event = {
        "companyCen": company_cen,
        "productCen": product_cen,
        "productCode": product_code,
        "productName": product_name,
        "quantity": float(quantity),
        "newStock": float(new_stock),
        "warehouseCen": warehouse_cen,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
    }
    with restock_lock:
        for sub in restock_subscribers:
            if sub["company_cen"].lower() == company_cen.lower():
                sub["queue"].put(event)

def get_company(company_cen):
    """Retrieve active company by CEN GUID, auto-creating it if missing for seamless interoperability."""
    company = query("SELECT * FROM empresas WHERE cen = %s AND activo = 1", (company_cen,), fetch='one')
    if not company:
        execute(
            "INSERT INTO empresas (cen, nombre, nit, activo) VALUES (%s, %s, %s, 1) ON CONFLICT (cen) DO NOTHING",
            (company_cen, f"Empresa {company_cen[:8]}", "20123456789")
        )
        company = query("SELECT * FROM empresas WHERE cen = %s AND activo = 1", (company_cen,), fetch='one')
    return company

def datetime_now_str():
    return datetime.datetime.now().isoformat()

# ==========================================
# 1. COMPANIES ENDPOINTS
# ==========================================

@bp.route('/api/inventory/companies', methods=['GET'])
def get_companies():
    try:
        companies = query("SELECT * FROM empresas WHERE activo = 1")
        return jsonify([{
            'cen': c['cen'],
            'name': c['nombre'],
            'nit': c['nit'],
            'active': bool(c['activo'])
        } for c in companies])
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/inventory/companies/<company_cen>', methods=['GET'])
def get_company_detail(company_cen):
    try:
        c = get_company(company_cen)
        if not c:
            return jsonify({'error': 'Company not found'}), 404
        return jsonify({
            'cen': c['cen'],
            'name': c['nombre'],
            'nit': c['nit'],
            'active': bool(c['activo'])
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# ==========================================
# 2. CATEGORIES ENDPOINTS
# ==========================================

@bp.route('/api/inventory/companies/<company_cen>/categories', methods=['GET'])
def get_categories(company_cen):
    try:
        c = get_company(company_cen)
        if not c: return jsonify({'error': 'Company not found'}), 404
        
        categories = query("SELECT * FROM categorias ORDER BY nombre ASC")
        return jsonify([{
            'cen': cat['cen'],
            'code': cat['code'],
            'name': cat['nombre'],
            'active': True
        } for cat in categories])
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/inventory/companies/<company_cen>/categories', methods=['POST'])
def create_category(company_cen):
    try:
        c = get_company(company_cen)
        if not c: return jsonify({'error': 'Company not found'}), 404
        
        data = request.get_json() or {}
        name = data.get('name', '').strip()
        if not name: return jsonify({'error': 'Category name is required'}), 400
        
        exists = query("SELECT id FROM categorias WHERE nombre = %s", (name,), fetch='one')
        if exists: return jsonify({'error': 'Category already exists'}), 400
        
        new_cen = str(uuid.uuid4())
        count = query("SELECT COUNT(*) as count FROM categorias", fetch='one')['count']
        new_code = f"CAT-{count+1:05d}"
        
        execute("INSERT INTO categorias (nombre, cen, code) VALUES (%s, %s, %s)", (name, new_cen, new_code))
        return jsonify({
            'cen': new_cen,
            'code': new_code,
            'name': name,
            'active': True
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/inventory/companies/<company_cen>/categories/<category_cen>', methods=['PUT'])
def update_category(company_cen, category_cen):
    try:
        c = get_company(company_cen)
        if not c: return jsonify({'error': 'Company not found'}), 404
        
        cat = query("SELECT * FROM categorias WHERE cen = %s", (category_cen,), fetch='one')
        if not cat: return jsonify({'error': 'Category not found'}), 404
        
        data = request.get_json() or {}
        name = data.get('name', '').strip()
        if not name: return jsonify({'error': 'Category name is required'}), 400
        
        exists = query("SELECT id FROM categorias WHERE nombre = %s AND cen != %s", (name, category_cen), fetch='one')
        if exists: return jsonify({'error': 'Another category with this name already exists'}), 400
        
        execute("UPDATE categorias SET nombre = %s WHERE cen = %s", (name, category_cen))
        return jsonify({
            'cen': category_cen,
            'code': cat['code'],
            'name': name,
            'active': True
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# ==========================================
# 3. UNITS ENDPOINTS
# ==========================================

@bp.route('/api/inventory/companies/<company_cen>/units', methods=['GET'])
def get_units(company_cen):
    try:
        c = get_company(company_cen)
        if not c: return jsonify({'error': 'Company not found'}), 404
        
        units = query("SELECT * FROM unidades ORDER BY nombre ASC")
        return jsonify([{
            'cen': u['cen'],
            'code': u['code'],
            'name': u['nombre'],
            'abbreviation': u['nombre'][:3].upper(),
            'active': True
        } for u in units])
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/inventory/companies/<company_cen>/units', methods=['POST'])
def create_unit(company_cen):
    try:
        c = get_company(company_cen)
        if not c: return jsonify({'error': 'Company not found'}), 404
        
        data = request.get_json() or {}
        name = data.get('name', '').strip()
        if not name: return jsonify({'error': 'Unit name is required'}), 400
        
        exists = query("SELECT id FROM unidades WHERE nombre = %s", (name,), fetch='one')
        if exists: return jsonify({'error': 'Unit already exists'}), 400
        
        new_cen = str(uuid.uuid4())
        count = query("SELECT COUNT(*) as count FROM unidades", fetch='one')['count']
        new_code = f"UNI-{count+1:05d}"
        
        execute("INSERT INTO unidades (nombre, cen, code) VALUES (%s, %s, %s)", (name, new_cen, new_code))
        return jsonify({
            'cen': new_cen,
            'code': new_code,
            'name': name,
            'abbreviation': name[:3].upper(),
            'active': True
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/inventory/companies/<company_cen>/units/<unit_cen>', methods=['PUT'])
def update_unit(company_cen, unit_cen):
    try:
        c = get_company(company_cen)
        if not c: return jsonify({'error': 'Company not found'}), 404
        
        u = query("SELECT * FROM unidades WHERE cen = %s", (unit_cen,), fetch='one')
        if not u: return jsonify({'error': 'Unit not found'}), 404
        
        data = request.get_json() or {}
        name = data.get('name', '').strip()
        if not name: return jsonify({'error': 'Unit name is required'}), 400
        
        exists = query("SELECT id FROM unidades WHERE nombre = %s AND cen != %s", (name, unit_cen), fetch='one')
        if exists: return jsonify({'error': 'Another unit with this name already exists'}), 400
        
        execute("UPDATE unidades SET nombre = %s WHERE cen = %s", (name, unit_cen))
        return jsonify({
            'cen': unit_cen,
            'code': u['code'],
            'name': name,
            'abbreviation': name[:3].upper(),
            'active': True
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# ==========================================
# 4. PRODUCTS ENDPOINTS
# ==========================================

@bp.route('/api/inventory/companies/<company_cen>/products', methods=['GET'])
def get_products(company_cen):
    try:
        c = get_company(company_cen)
        if not c: return jsonify({'error': 'Company not found'}), 404
        
        search = request.args.get('search', '').strip()
        category_cen = request.args.get('categoryCen', '').strip()
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('pageSize', 100, type=int)
        
        sql = '''
            SELECT p.*, c.cen as category_cen, c.nombre as category_name, c.code as category_code,
                   u.cen as unit_cen, u.nombre as unit_name, u.code as unit_code
            FROM productos p
            JOIN categorias c ON c.id = p.categoria_id
            JOIN unidades u ON u.id = p.unidad_id
            WHERE 1=1
        '''
        params = []
        
        if search:
            sql += ' AND (LOWER(p.nombre) LIKE LOWER(%s) OR LOWER(p.code) LIKE LOWER(%s))'
            params.extend([f'%{search}%', f'%{search}%'])
            
        if category_cen:
            sql += ' AND c.cen = %s'
            params.append(category_cen)
            
        # PostgreSQL doesn't support subqueries as tables without alias
        count_sql = f"SELECT COUNT(*) as count FROM ({sql}) AS sub"
        total_count = query(count_sql, tuple(params) if params else None, fetch='one')['count']
        
        sql += ' ORDER BY p.nombre ASC LIMIT %s OFFSET %s'
        offset = (page - 1) * page_size
        params.extend([page_size, offset])
        
        products = query(sql, tuple(params))
        
        items = []
        for p in products:
            items.append({
                'cen': p['cen'],
                'code': p['code'],
                'sku': p['nombre'].upper().replace(' ', '_'),
                'name': p['nombre'],
                'description': '',
                'categoryCen': p['category_cen'],
                'category': {
                    'categoriaId': p['category_cen'],
                    'nombre': p['category_name'],
                    'cenCode': p['category_code']
                },
                'unitCen': p['unit_cen'],
                'unidad': {
                    'unidadId': p['unit_cen'],
                    'nombre': p['unit_name'],
                    'cenCode': p['unit_code']
                },
                'price': float(p['precio']),
                'cost': 0,
                'stock': int(p['stock']),
                'trackStock': True,
                'isOutOfStock': bool(p['agotado'] or p['stock'] <= 0),
                'active': bool(p['activo']),
                'stationCode': p['station_code'] or 'COCINA'
            })
            
        return jsonify({
            'items': items,
            'totalCount': total_count,
            'page': page,
            'pageSize': page_size
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/inventory/companies/<company_cen>/sellable-products', methods=['GET'])
def get_sellable_products(company_cen):
    try:
        c = get_company(company_cen)
        if not c: return jsonify({'error': 'Company not found'}), 404
        
        search = request.args.get('search', '').strip()
        category_cen = request.args.get('categoryCen', '').strip()
        only_available = request.args.get('onlyAvailable', 'true').lower() == 'true'
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('pageSize', 100, type=int)
        
        sql = '''
            SELECT p.*, c.cen as category_cen, c.nombre as category_name, c.code as category_code,
                   u.cen as unit_cen, u.nombre as unit_name, u.code as unit_code
            FROM productos p
            JOIN categorias c ON c.id = p.categoria_id
            JOIN unidades u ON u.id = p.unidad_id
            WHERE p.activo = 1
        '''
        params = []
        
        if only_available:
            sql += ' AND p.agotado = 0 AND p.stock > 0'
            
        if search:
            sql += ' AND LOWER(p.nombre) LIKE LOWER(%s)'
            params.append(f'%{search}%')
            
        if category_cen:
            sql += ' AND c.cen = %s'
            params.append(category_cen)
            
        count_sql = f"SELECT COUNT(*) as count FROM ({sql}) AS sub"
        total_count = query(count_sql, tuple(params) if params else None, fetch='one')['count']
        
        sql += ' ORDER BY p.nombre ASC LIMIT %s OFFSET %s'
        offset = (page - 1) * page_size
        params.extend([page_size, offset])
        
        products = query(sql, tuple(params))
        
        items = []
        for p in products:
            items.append({
                'cen': p['cen'],
                'code': p['code'],
                'sku': p['nombre'].upper().replace(' ', '_'),
                'name': p['nombre'],
                'description': '',
                'categoryCen': p['category_cen'],
                'category': {
                    'categoriaId': p['category_cen'],
                    'nombre': p['category_name'],
                    'cenCode': p['category_code']
                },
                'unitCen': p['unit_cen'],
                'unidad': {
                    'unidadId': p['unit_cen'],
                    'nombre': p['unit_name'],
                    'cenCode': p['unit_code']
                },
                'price': float(p['precio']),
                'cost': 0,
                'stock': int(p['stock']),
                'trackStock': True,
                'isOutOfStock': bool(p['agotado'] or p['stock'] <= 0),
                'active': bool(p['activo']),
                'stationCode': p['station_code'] or 'COCINA'
            })
            
        return jsonify({
            'items': items,
            'totalCount': total_count,
            'page': page,
            'pageSize': page_size
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/inventory/companies/<company_cen>/products', methods=['POST'])
def create_product(company_cen):
    try:
        c = get_company(company_cen)
        if not c: return jsonify({'error': 'Company not found'}), 404
        
        data = request.get_json() or {}
        nombre = data.get('name', '').strip()
        category_cen = data.get('categoryCen', '').strip()
        unit_cen = data.get('unitCen', '').strip()
        precio = data.get('price', 0.0)
        stock = data.get('stock', 0)
        station_code = data.get('stationCode', 'COCINA').upper()
        
        if not nombre: return jsonify({'error': 'Product name is required'}), 400
        if not category_cen: return jsonify({'error': 'Category CEN is required'}), 400
        if not unit_cen: return jsonify({'error': 'Unit CEN is required'}), 400
        
        cat = query("SELECT id FROM categorias WHERE cen = %s", (category_cen,), fetch='one')
        if not cat: return jsonify({'error': 'Category not found'}), 400
        
        u = query("SELECT id FROM unidades WHERE cen = %s", (unit_cen,), fetch='one')
        if not u: return jsonify({'error': 'Unit not found'}), 400
        
        new_cen = str(uuid.uuid4())
        count = query("SELECT COUNT(*) as count FROM productos", fetch='one')['count']
        new_code = f"PRO-{count+1:05d}"
        
        execute('''
            INSERT INTO productos (nombre, categoria_id, unidad_id, precio, stock, activo, agotado, cen, code, station_code)
            VALUES (%s, %s, %s, %s, %s, 1, 0, %s, %s, %s)
        ''', (nombre, cat['id'], u['id'], precio, stock, new_cen, new_code, station_code))
        
        return jsonify({
            'cen': new_cen,
            'code': new_code,
            'sku': nombre.upper().replace(' ', '_'),
            'name': nombre,
            'description': '',
            'categoryCen': category_cen,
            'unitCen': unit_cen,
            'price': precio,
            'cost': 0,
            'stock': int(stock),
            'trackStock': True,
            'isOutOfStock': False,
            'active': True,
            'stationCode': station_code
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/inventory/companies/<company_cen>/products/<product_cen>', methods=['PUT'])
def update_product(company_cen, product_cen):
    try:
        c = get_company(company_cen)
        if not c: return jsonify({'error': 'Company not found'}), 404
        
        prod = query("SELECT id, code, stock FROM productos WHERE cen = %s", (product_cen,), fetch='one')
        if not prod: return jsonify({'error': 'Product not found'}), 404
        
        data = request.get_json() or {}
        nombre = data.get('name', '').strip()
        category_cen = data.get('categoryCen', '').strip()
        unit_cen = data.get('unitCen', '').strip()
        precio = data.get('price', 0.0)
        station_code = data.get('stationCode', 'COCINA').upper()
        
        cat = query("SELECT id FROM categorias WHERE cen = %s", (category_cen,), fetch='one')
        if not cat: return jsonify({'error': 'Category not found'}), 400
        
        u = query("SELECT id FROM unidades WHERE cen = %s", (unit_cen,), fetch='one')
        if not u: return jsonify({'error': 'Unit not found'}), 400
        
        execute('''
            UPDATE productos 
            SET nombre = %s, categoria_id = %s, unidad_id = %s, precio = %s, station_code = %s
            WHERE cen = %s
        ''', (nombre, cat['id'], u['id'], precio, station_code, product_cen))
        
        return jsonify({
            'cen': product_cen,
            'code': prod['code'],
            'sku': nombre.upper().replace(' ', '_'),
            'name': nombre,
            'description': '',
            'categoryCen': category_cen,
            'unitCen': unit_cen,
            'price': precio,
            'cost': 0,
            'stock': int(prod['stock']),
            'trackStock': True,
            'isOutOfStock': False,
            'active': True,
            'stationCode': station_code
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/inventory/companies/<company_cen>/products/<product_cen>/status', methods=['PATCH'])
def update_product_status(company_cen, product_cen):
    try:
        c = get_company(company_cen)
        if not c: return jsonify({'error': 'Company not found'}), 404
        
        prod = query("SELECT id FROM productos WHERE cen = %s", (product_cen,), fetch='one')
        if not prod: return jsonify({'error': 'Product not found'}), 404
        
        data = request.get_json() or {}
        active = data.get('active')
        is_out_of_stock = data.get('isOutOfStock')
        
        updates = []
        params = []
        if active is not None:
            updates.append("activo = %s")
            params.append(1 if active else 0)
        if is_out_of_stock is not None:
            updates.append("agotado = %s")
            params.append(1 if is_out_of_stock else 0)
            
        if updates:
            params.append(product_cen)
            execute(f"UPDATE productos SET {', '.join(updates)} WHERE cen = %s", tuple(params))
            
        updated = query("SELECT * FROM productos WHERE cen = %s", (product_cen,), fetch='one')
        cat = query("SELECT cen FROM categorias WHERE id = %s", (updated['categoria_id'],), fetch='one')
        u = query("SELECT cen FROM unidades WHERE id = %s", (updated['unidad_id'],), fetch='one')
        
        return jsonify({
            'cen': product_cen,
            'code': updated['code'],
            'sku': updated['nombre'].upper().replace(' ', '_'),
            'name': updated['nombre'],
            'description': '',
            'categoryCen': cat['cen'] if cat else '',
            'unitCen': u['cen'] if u else '',
            'price': float(updated['precio']),
            'cost': 0,
            'stock': int(updated['stock']),
            'trackStock': True,
            'isOutOfStock': bool(updated['agotado']),
            'active': bool(updated['activo']),
            'stationCode': updated['station_code'] or 'COCINA'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/inventory/companies/<company_cen>/products/lookup', methods=['POST'])
def lookup_products(company_cen):
    try:
        c = get_company(company_cen)
        if not c: return jsonify({'error': 'Company not found'}), 404
        
        data = request.get_json() or {}
        product_cens = data.get('productCens', [])
        
        if not product_cens:
            return jsonify([])
            
        placeholders = ', '.join('%s' for _ in product_cens)
        sql = f'''
            SELECT p.*, c.cen as category_cen, u.cen as unit_cen
            FROM productos p
            LEFT JOIN categorias c ON c.id = p.categoria_id
            LEFT JOIN unidades u ON u.id = p.unidad_id
            WHERE p.cen IN ({placeholders})
        '''
        products = query(sql, tuple(product_cens))
        
        res = []
        for p in products:
            res.append({
                'cen': p['cen'],
                'code': p['code'],
                'sku': p['nombre'].upper().replace(' ', '_'),
                'name': p['nombre'],
                'description': '',
                'categoryCen': p['category_cen'],
                'unitCen': p['unit_cen'],
                'price': float(p['precio']),
                'cost': 0,
                'stock': int(p['stock']),
                'trackStock': True,
                'isOutOfStock': bool(p['agotado'] or p['stock'] <= 0),
                'active': bool(p['activo']),
                'stationCode': p['station_code'] or 'COCINA'
            })
        return jsonify(res)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# ==========================================
# 5. STOCK & ADJUSTMENTS ENDPOINTS
# ==========================================

@bp.route('/api/inventory/companies/<company_cen>/stock', methods=['GET'])
def get_stock(company_cen):
    try:
        c = get_company(company_cen)
        if not c: return jsonify({'error': 'Company not found'}), 404
        
        products = query("SELECT cen, code, stock, nombre FROM productos")
        return jsonify([{
            'productCen': p['cen'],
            'productCode': p['code'],
            'quantity': p['stock'],
            'minQuantity': 5,
            'lowStock': p['stock'] < 5
        } for p in products])
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/inventory/companies/<company_cen>/stock/validate', methods=['POST'])
def stock_validate(company_cen):
    try:
        c = get_company(company_cen)
        if not c: return jsonify({'error': 'Company not found'}), 404
        
        data = request.get_json() or {}
        product_cen = data.get('productCen')
        qty = data.get('quantity', 0)
        
        prod = query("SELECT stock FROM productos WHERE cen = %s", (product_cen,), fetch='one')
        if not prod:
            return jsonify({'available': False, 'quantity': 0})
            
        return jsonify({
            'available': prod['stock'] >= qty,
            'quantity': prod['stock']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/inventory/companies/<company_cen>/stock/consume', methods=['POST'])
def stock_consume(company_cen):
    try:
        c = get_company(company_cen)
        if not c: return jsonify({'error': 'Company not found'}), 404
        
        data = request.get_json() or {}
        product_cen = data.get('productCen')
        qty = data.get('quantity', 0)
        notes = data.get('notes', 'Ticket payment')
        
        prod = query("SELECT id, stock FROM productos WHERE cen = %s", (product_cen,), fetch='one')
        if not prod:
            return jsonify({'error': 'Product not found'}), 404
            
        if prod['stock'] < qty:
            return jsonify({'error': 'Insufficient stock'}), 409
            
        execute("UPDATE productos SET stock = stock - %s WHERE cen = %s", (qty, product_cen))
        execute("INSERT INTO ajustes_stock (producto_id, tipo, cantidad, motivo, creado_en) VALUES (%s, 'salida', %s, %s, CURRENT_TIMESTAMP)", (prod['id'], qty, notes))
        
        return jsonify({'message': 'Stock consumed successfully', 'newStock': prod['stock'] - qty})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/inventory/companies/<company_cen>/restock-events', methods=['GET'])
def restock_events(company_cen):
    def event_stream():
        q = queue.Queue()
        with restock_lock:
            restock_subscribers.append({"company_cen": company_cen, "queue": q})
        try:
            while True:
                try:
                    event = q.get(timeout=15)
                    yield f"data: {json.dumps(event)}\n\n"
                except queue.Empty:
                    yield ": keep-alive\n\n"
        finally:
            with restock_lock:
                for sub in list(restock_subscribers):
                    if sub["queue"] is q:
                        restock_subscribers.remove(sub)
                        break

    return Response(event_stream(), content_type='text/event-stream', headers={
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'X-Accel-Buffering': 'no'
    })

@bp.route('/api/inventory/companies/<company_cen>/stock/increase', methods=['POST'])
def stock_increase(company_cen):
    try:
        c = get_company(company_cen)
        if not c: return jsonify({'error': 'Company not found'}), 404
        
        data = request.get_json() or {}
        product_cen = data.get('productCen')
        qty = data.get('quantity', 0)
        notes = data.get('notes', 'Stock adjustment')
        
        prod = query("SELECT id, name, code, stock FROM productos WHERE cen = %s", (product_cen,), fetch='one')
        if not prod:
            return jsonify({'error': 'Product not found'}), 404
            
        execute("UPDATE productos SET stock = stock + %s WHERE cen = %s", (qty, product_cen))
        execute("INSERT INTO ajustes_stock (producto_id, tipo, cantidad, motivo, creado_en) VALUES (%s, 'entrada', %s, %s, CURRENT_TIMESTAMP)", (prod['id'], qty, notes))
        
        broadcast_restock(
            company_cen=company_cen,
            product_cen=product_cen,
            product_code=prod['code'] or product_cen,
            product_name=prod['name'] or "Producto",
            quantity=qty,
            new_stock=prod['stock'] + qty,
            warehouse_cen=data.get('warehouseCen') or 'alm-cen-guid-1'
        )
        
        return jsonify({'message': 'Stock increased successfully', 'newStock': prod['stock'] + qty})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/inventory/companies/<company_cen>/stock/adjustments', methods=['POST'])
def register_stock_adjustment(company_cen):
    try:
        c = get_company(company_cen)
        if not c: return jsonify({'error': 'Company not found'}), 404
        
        data = request.get_json() or {}
        product_cen = data.get('productCen')
        qty = data.get('quantity', 0)
        reason = data.get('reason', '').strip()
        
        if not product_cen: return jsonify({'error': 'Product CEN is required'}), 400
        if qty == 0: return jsonify({'error': 'Quantity must not be 0'}), 400
        
        prod = query("SELECT id, name, code, stock FROM productos WHERE cen = %s", (product_cen,), fetch='one')
        if not prod: return jsonify({'error': 'Product not found'}), 404
        
        tipo = 'entrada' if qty > 0 else 'salida'
        abs_qty = abs(qty)
        
        if tipo == 'salida' and prod['stock'] < abs_qty:
            return jsonify({'error': f'Stock insuficiente. Disponible: {prod["stock"]}'}), 400
            
        new_cen = str(uuid.uuid4())
        execute('''
            INSERT INTO ajustes_stock (producto_id, tipo, cantidad, motivo, creado_en)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
        ''', (prod['id'], tipo, abs_qty, reason))
        
        if tipo == 'entrada':
            execute("UPDATE productos SET stock = stock + %s WHERE id = %s", (abs_qty, prod['id']))
            broadcast_restock(
                company_cen=company_cen,
                product_cen=product_cen,
                product_code=prod['code'] or product_cen,
                product_name=prod['name'] or "Producto",
                quantity=abs_qty,
                new_stock=prod['stock'] + abs_qty,
                warehouse_cen=data.get('warehouseCen') or 'alm-cen-guid-1'
            )
        else:
            execute("UPDATE productos SET stock = stock - %s WHERE id = %s", (abs_qty, prod['id']))
            
        return jsonify({
            'cen': new_cen,
            'productCen': product_cen,
            'quantity': qty,
            'reason': reason
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# ==========================================
# 6. DASHBOARD ENDPOINT
# ==========================================

@bp.route('/api/inventory/companies/<company_cen>/dashboard', methods=['GET'])
def inventory_dashboard(company_cen):
    try:
        c = get_company(company_cen)
        if not c: return jsonify({'error': 'Company not found'}), 404
        
        total_products = query("SELECT COUNT(*) as count FROM productos", fetch='one')['count']
        total_stock_value = query("SELECT SUM(precio * stock) as value FROM productos", fetch='one')['value'] or 0.0
        
        return jsonify({
            'totalProducts': total_products,
            'totalStockValue': round(float(total_stock_value), 2)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# ==========================================
# 7. ADDED CONTRACT ENDPOINTS
# ==========================================

@bp.route('/api/inventory/companies/<company_cen>/warehouses', methods=['GET'])
def get_warehouses(company_cen):
    try:
        c = get_company(company_cen)
        if not c: return jsonify({'error': 'Company not found'}), 404
        
        warehouses = query("SELECT cen, nombre, activo FROM bodegas ORDER BY nombre ASC")
        return jsonify([{
            'warehouseCen': w['cen'],
            'name': w['nombre'],
            'isActive': bool(w['activo'])
        } for w in warehouses])
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/inventory/companies/<company_cen>/documents', methods=['GET'])
def get_documents(company_cen):
    try:
        c = get_company(company_cen)
        if not c: return jsonify({'error': 'Company not found'}), 404
        
        doc_type = request.args.get('documentType')
        from_date = request.args.get('from')
        to_date = request.args.get('to')
        
        sql = "SELECT d.*, (SELECT COALESCE(SUM(cantidad), 0) FROM documentos_items WHERE documento_id = d.id) as total_items FROM documentos d WHERE 1=1"
        params = []
        if doc_type:
            sql += " AND d.tipo = %s"
            params.append(doc_type)
        if from_date:
            sql += " AND d.creado_en >= %s"
            params.append(from_date)
        if to_date:
            sql += " AND d.creado_en <= %s"
            params.append(to_date)
            
        sql += " ORDER BY d.creado_en DESC"
        
        docs = query(sql, tuple(params) if params else None)
        return jsonify([{
            'documentCen': d['cen'],
            'documentType': d['tipo'],
            'status': d['estado'],
            'title': f"Documento {d['tipo']} - {d['cen'][:8]}",
            'createdAt': d['creado_en'].isoformat() if hasattr(d['creado_en'], 'isoformat') else d['creado_en'],
            'totalItems': float(d['total_items']),
            'generatedMovementCens': []
        } for d in docs])
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/inventory/companies/<company_cen>/documents', methods=['POST'])
def create_document(company_cen):
    try:
        c = get_company(company_cen)
        if not c: return jsonify({'error': 'Company not found'}), 404
        
        data = request.get_json() or {}
        doc_type = data.get('documentType', 'ADJUSTMENT').upper()
        warehouse_cen = data.get('warehouseCen') or 'alm-cen-guid-1'
        reason = data.get('reason', '')
        ext_ref = data.get('externalReference', '')
        lines = data.get('lines', [])
        
        if not lines:
            return jsonify({'error': 'Lines are required'}), 400
            
        # Create document
        new_doc_cen = str(uuid.uuid4())
        doc_id = execute('''
            INSERT INTO documentos (cen, tipo, estado, referencia, notas, creado_en)
            VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        ''', (new_doc_cen, doc_type, 'CONFIRMED', ext_ref, reason))
        
        movement_cens = []
        for line in lines:
            prod_cen = line.get('productCen')
            qty = line.get('quantity', 0)
            cost = line.get('unitCost', 0)
            
            if not prod_cen or qty == 0:
                continue
                
            prod = query("SELECT id, name, code, stock FROM productos WHERE cen = %s", (prod_cen,), fetch='one')
            if not prod:
                continue
                
            # Save line
            execute('''
                INSERT INTO documentos_items (documento_id, producto_cen, cantidad, costo_unitario, creado_en)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
            ''', (doc_id, prod_cen, qty, cost))
            
            # Adjust stock
            tipo_mov = 'entrada' if qty > 0 else 'salida'
            abs_qty = abs(qty)
            
            # Compatibility with legacy ajustes_stock table
            execute('''
                INSERT INTO ajustes_stock (producto_id, tipo, cantidad, motivo, creado_en)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
            ''', (prod['id'], tipo_mov, abs_qty, f"Doc {doc_type}: {reason}"))
            
            if qty > 0:
                execute("UPDATE productos SET stock = stock + %s WHERE id = %s", (abs_qty, prod['id']))
                broadcast_restock(
                    company_cen=company_cen,
                    product_cen=prod_cen,
                    product_code=prod['code'] or prod_cen,
                    product_name=prod['name'] or "Producto",
                    quantity=abs_qty,
                    new_stock=prod['stock'] + abs_qty,
                    warehouse_cen=warehouse_cen
                )
            else:
                execute("UPDATE productos SET stock = stock - %s WHERE id = %s", (abs_qty, prod['id']))
                
            # Record in kardex
            mov_cen = str(uuid.uuid4())
            movement_cens.append(mov_cen)
            execute('''
                INSERT INTO kardex (movimiento_cen, documento_cen, producto_cen, bodega_cen, tipo_movimiento, cantidad, costo_unitario, motivo, creado_en)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ''', (mov_cen, new_doc_cen, prod_cen, warehouse_cen, doc_type, qty, cost, reason))
            
        return jsonify({
            'documentCen': new_doc_cen,
            'documentType': doc_type,
            'status': 'CONFIRMED',
            'title': f"Documento {doc_type} - {new_doc_cen[:8]}",
            'createdAt': datetime_now_str(),
            'totalItems': len(lines),
            'generatedMovementCens': movement_cens
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/inventory/companies/<company_cen>/products/<product_cen>/kardex', methods=['GET'])
def get_product_kardex(company_cen, product_cen):
    try:
        c = get_company(company_cen)
        if not c: return jsonify({'error': 'Company not found'}), 404
        
        prod = query("SELECT id FROM productos WHERE cen = %s", (product_cen,), fetch='one')
        if not prod: return jsonify({'error': 'Product not found'}), 404
        
        movements = query("SELECT * FROM kardex WHERE producto_cen = %s ORDER BY creado_en DESC", (product_cen,))
        
        # Fallback to legacy ajustes_stock if kardex is empty
        if not movements:
            ajustes = query('''
                SELECT a.*, p.cen as prod_cen 
                FROM ajustes_stock a 
                JOIN productos p ON p.id = a.producto_id 
                WHERE p.cen = %s 
                ORDER BY a.creado_en DESC
            ''', (product_cen,))
            return jsonify([{
                'movementCen': f"mov-ajuste-{a['id']}",
                'documentCen': None,
                'productCen': a['prod_cen'],
                'warehouseCen': 'alm-cen-guid-1',
                'movementType': 'ADJUSTMENT',
                'quantity': float(a['cantidad']) if a['tipo'] == 'entrada' else -float(a['cantidad']),
                'unitCost': 0.0,
                'reason': a['motivo'],
                'createdAt': a['creado_en'].isoformat() if hasattr(a['creado_en'], 'isoformat') else a['creado_en']
            } for a in ajustes])
            
        return jsonify([{
            'movementCen': m['movimiento_cen'],
            'documentCen': m['documento_cen'],
            'productCen': m['producto_cen'],
            'warehouseCen': m['bodega_cen'],
            'movementType': m['tipo_movimiento'],
            'quantity': float(m['cantidad']),
            'unitCost': float(m['costo_unitario']) if m['costo_unitario'] is not None else None,
            'reason': m['motivo'],
            'createdAt': m['creado_en'].isoformat() if hasattr(m['creado_en'], 'isoformat') else m['creado_en']
        } for m in movements])
    except Exception as e:
        return jsonify({'error': str(e)}), 400

