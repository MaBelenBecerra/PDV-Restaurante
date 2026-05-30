from flask import Blueprint, request, jsonify
import uuid
import datetime
from database import query, execute

bp = Blueprint('inventory', __name__)

def get_company(company_cen):
    """Retrieve active company by CEN GUID, auto-creating it if missing for seamless interoperability."""
    company = query("SELECT * FROM empresas WHERE cen = ? AND activo = 1", (company_cen,), fetch='one')
    if not company:
        execute(
            "INSERT OR IGNORE INTO empresas (cen, nombre, nit, activo) VALUES (?, ?, ?, 1)",
            (company_cen, f"Empresa {company_cen[:8]}", "20123456789")
        )
        company = query("SELECT * FROM empresas WHERE cen = ? AND activo = 1", (company_cen,), fetch='one')
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
        
        exists = query("SELECT id FROM categorias WHERE nombre = ?", (name,), fetch='one')
        if exists: return jsonify({'error': 'Category already exists'}), 400
        
        new_cen = str(uuid.uuid4())
        count = query("SELECT COUNT(*) as count FROM categorias", fetch='one')['count']
        new_code = f"CAT-{count+1:05d}"
        
        execute("INSERT INTO categorias (nombre, cen, code) VALUES (?, ?, ?)", (name, new_cen, new_code))
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
        
        cat = query("SELECT * FROM categorias WHERE cen = ?", (category_cen,), fetch='one')
        if not cat: return jsonify({'error': 'Category not found'}), 404
        
        data = request.get_json() or {}
        name = data.get('name', '').strip()
        if not name: return jsonify({'error': 'Category name is required'}), 400
        
        exists = query("SELECT id FROM categorias WHERE nombre = ? AND cen != ?", (name, category_cen), fetch='one')
        if exists: return jsonify({'error': 'Another category with this name already exists'}), 400
        
        execute("UPDATE categorias SET nombre = ? WHERE cen = ?", (name, category_cen))
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
        
        exists = query("SELECT id FROM unidades WHERE nombre = ?", (name,), fetch='one')
        if exists: return jsonify({'error': 'Unit already exists'}), 400
        
        new_cen = str(uuid.uuid4())
        count = query("SELECT COUNT(*) as count FROM unidades", fetch='one')['count']
        new_code = f"UNI-{count+1:05d}"
        
        execute("INSERT INTO unidades (nombre, cen, code) VALUES (?, ?, ?)", (name, new_cen, new_code))
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
        
        u = query("SELECT * FROM unidades WHERE cen = ?", (unit_cen,), fetch='one')
        if not u: return jsonify({'error': 'Unit not found'}), 404
        
        data = request.get_json() or {}
        name = data.get('name', '').strip()
        if not name: return jsonify({'error': 'Unit name is required'}), 400
        
        exists = query("SELECT id FROM unidades WHERE nombre = ? AND cen != ?", (name, unit_cen), fetch='one')
        if exists: return jsonify({'error': 'Another unit with this name already exists'}), 400
        
        execute("UPDATE unidades SET nombre = ? WHERE cen = ?", (name, unit_cen))
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
            sql += ' AND (LOWER(p.nombre) LIKE LOWER(?) OR LOWER(p.code) LIKE LOWER(?))'
            params.extend([f'%{search}%', f'%{search}%'])
            
        if category_cen:
            sql += ' AND c.cen = ?'
            params.append(category_cen)
            
        count_sql = f"SELECT COUNT(*) as count FROM ({sql})"
        total_count = query(count_sql, tuple(params) if params else None, fetch='one')['count']
        
        sql += ' ORDER BY p.nombre ASC LIMIT ? OFFSET ?'
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
                'price': p['precio'],
                'cost': 0,
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
            sql += ' AND LOWER(p.nombre) LIKE LOWER(?)'
            params.append(f'%{search}%')
            
        if category_cen:
            sql += ' AND c.cen = ?'
            params.append(category_cen)
            
        count_sql = f"SELECT COUNT(*) as count FROM ({sql})"
        total_count = query(count_sql, tuple(params) if params else None, fetch='one')['count']
        
        sql += ' ORDER BY p.nombre ASC LIMIT ? OFFSET ?'
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
                'price': p['precio'],
                'cost': 0,
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
        
        cat = query("SELECT id FROM categorias WHERE cen = ?", (category_cen,), fetch='one')
        if not cat: return jsonify({'error': 'Category not found'}), 400
        
        u = query("SELECT id FROM unidades WHERE cen = ?", (unit_cen,), fetch='one')
        if not u: return jsonify({'error': 'Unit not found'}), 400
        
        new_cen = str(uuid.uuid4())
        count = query("SELECT COUNT(*) as count FROM productos", fetch='one')['count']
        new_code = f"PRO-{count+1:05d}"
        
        execute('''
            INSERT INTO productos (nombre, categoria_id, unidad_id, precio, stock, activo, agotado, cen, code, station_code)
            VALUES (?, ?, ?, ?, ?, 1, 0, ?, ?, ?)
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
        
        prod = query("SELECT id, code FROM productos WHERE cen = ?", (product_cen,), fetch='one')
        if not prod: return jsonify({'error': 'Product not found'}), 404
        
        data = request.get_json() or {}
        nombre = data.get('name', '').strip()
        category_cen = data.get('categoryCen', '').strip()
        unit_cen = data.get('unitCen', '').strip()
        precio = data.get('price', 0.0)
        station_code = data.get('stationCode', 'COCINA').upper()
        
        cat = query("SELECT id FROM categorias WHERE cen = ?", (category_cen,), fetch='one')
        if not cat: return jsonify({'error': 'Category not found'}), 400
        
        u = query("SELECT id FROM unidades WHERE cen = ?", (unit_cen,), fetch='one')
        if not u: return jsonify({'error': 'Unit not found'}), 400
        
        execute('''
            UPDATE productos 
            SET nombre = ?, categoria_id = ?, unidad_id = ?, precio = ?, station_code = ?
            WHERE cen = ?
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
        
        prod = query("SELECT id FROM productos WHERE cen = ?", (product_cen,), fetch='one')
        if not prod: return jsonify({'error': 'Product not found'}), 404
        
        data = request.get_json() or {}
        active = data.get('active')
        is_out_of_stock = data.get('isOutOfStock')
        
        updates = []
        params = []
        if active is not None:
            updates.append("activo = ?")
            params.append(1 if active else 0)
        if is_out_of_stock is not None:
            updates.append("agotado = ?")
            params.append(1 if is_out_of_stock else 0)
            
        if updates:
            params.append(product_cen)
            execute(f"UPDATE productos SET {', '.join(updates)} WHERE cen = ?", tuple(params))
            
        updated = query("SELECT * FROM productos WHERE cen = ?", (product_cen,), fetch='one')
        cat = query("SELECT cen FROM categorias WHERE id = ?", (updated['categoria_id'],), fetch='one')
        u = query("SELECT cen FROM unidades WHERE id = ?", (updated['unidad_id'],), fetch='one')
        
        return jsonify({
            'cen': product_cen,
            'code': updated['code'],
            'sku': updated['nombre'].upper().replace(' ', '_'),
            'name': updated['nombre'],
            'description': '',
            'categoryCen': cat['cen'] if cat else '',
            'unitCen': u['cen'] if u else '',
            'price': updated['precio'],
            'cost': 0,
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
            
        placeholders = ', '.join('?' for _ in product_cens)
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
                'price': p['precio'],
                'cost': 0,
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
        
        prod = query("SELECT stock FROM productos WHERE cen = ?", (product_cen,), fetch='one')
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
        
        prod = query("SELECT id, stock FROM productos WHERE cen = ?", (product_cen,), fetch='one')
        if not prod:
            return jsonify({'error': 'Product not found'}), 404
            
        if prod['stock'] < qty:
            return jsonify({'error': 'Insufficient stock'}), 409
            
        execute("UPDATE productos SET stock = stock - ? WHERE cen = ?", (qty, product_cen))
        execute("INSERT INTO ajustes_stock (producto_id, tipo, cantidad, motivo, creado_en) VALUES (?, 'salida', ?, ?, datetime('now'))", (prod['id'], qty, notes))
        
        return jsonify({'message': 'Stock consumed successfully', 'newStock': prod['stock'] - qty})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/inventory/companies/<company_cen>/stock/increase', methods=['POST'])
def stock_increase(company_cen):
    try:
        c = get_company(company_cen)
        if not c: return jsonify({'error': 'Company not found'}), 404
        
        data = request.get_json() or {}
        product_cen = data.get('productCen')
        qty = data.get('quantity', 0)
        notes = data.get('notes', 'Stock adjustment')
        
        prod = query("SELECT id, stock FROM productos WHERE cen = ?", (product_cen,), fetch='one')
        if not prod:
            return jsonify({'error': 'Product not found'}), 404
            
        execute("UPDATE productos SET stock = stock + ? WHERE cen = ?", (qty, product_cen))
        execute("INSERT INTO ajustes_stock (producto_id, tipo, cantidad, motivo, creado_en) VALUES (?, 'entrada', ?, ?, datetime('now'))", (prod['id'], qty, notes))
        
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
        
        prod = query("SELECT id, stock FROM productos WHERE cen = ?", (product_cen,), fetch='one')
        if not prod: return jsonify({'error': 'Product not found'}), 404
        
        tipo = 'entrada' if qty > 0 else 'salida'
        abs_qty = abs(qty)
        
        if tipo == 'salida' and prod['stock'] < abs_qty:
            return jsonify({'error': f'Stock insuficiente. Disponible: {prod["stock"]}'}), 400
            
        new_cen = str(uuid.uuid4())
        execute('''
            INSERT INTO ajustes_stock (producto_id, tipo, cantidad, motivo, creado_en)
            VALUES (?, ?, ?, ?, datetime('now'))
        ''', (prod['id'], tipo, abs_qty, reason))
        
        if tipo == 'entrada':
            execute("UPDATE productos SET stock = stock + ? WHERE id = ?", (abs_qty, prod['id']))
        else:
            execute("UPDATE productos SET stock = stock - ? WHERE id = ?", (abs_qty, prod['id']))
            
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
            'totalStockValue': round(total_stock_value, 2)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400
