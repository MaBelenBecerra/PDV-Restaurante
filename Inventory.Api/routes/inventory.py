from flask import Blueprint, request, jsonify, Response
import uuid
import datetime
import queue
import threading
import json
from database import query, execute

bp = Blueprint('inventory', __name__)

# SSE Event stream management
restock_lock = threading.Lock()
restock_queues = []

def broadcast_restock(product_name, quantity, company_cen):
    event_data = {
        'productName': product_name,
        'quantity': quantity,
        'companyCen': company_cen,
        'timestamp': datetime.datetime.now().isoformat()
    }
    with restock_lock:
        for q in restock_queues:
            q.put(event_data)

# ==========================================
# 1. COMPANIES ENDPOINTS
# ==========================================

@bp.route('/api/inventory/companies', methods=['GET'])
def inventory_get_companies():
    companies = query("SELECT cen as companyCen, nombre as name, activo::boolean as isActive FROM public.empresas")
    return jsonify(companies)

@bp.route('/api/inventory/companies', methods=['POST'])
def inventory_create_company():
    data = request.get_json() or {}
    name = data.get('name')
    if not name: return jsonify({'error': 'name is required'}), 400
    new_cen = str(uuid.uuid4())
    execute("INSERT INTO public.empresas (cen, nombre, activo) VALUES (%s, %s, 1)", (new_cen, name))
    return jsonify({'companyCen': new_cen, 'name': name, 'isActive': True}), 201

@bp.route('/api/inventory/companies/<company_cen>', methods=['GET'])
def inventory_get_company(company_cen):
    c = query("SELECT id as companyId, cen as companyCen, nombre as name FROM public.empresas WHERE cen = %s", (company_cen,), fetch='one')
    if not c: return jsonify({'error': 'Company not found'}), 404
    return jsonify(c)

@bp.route('/api/inventory/companies/<company_cen>', methods=['PUT'])
def inventory_update_company(company_cen):
    data = request.get_json() or {}
    name = data.get('name')
    if not name: return jsonify({'error': 'name is required'}), 400
    execute("UPDATE public.empresas SET nombre = %s WHERE cen = %s", (name, company_cen))
    return jsonify({'companyCen': company_cen, 'name': name, 'isActive': True})

# ==========================================
# 2. CATALOG ENDPOINTS
# ==========================================

@bp.route('/api/inventory/companies/<company_cen>/categories', methods=['GET'])
def inventory_get_categories(company_cen):
    cats = query("SELECT cen as categoryCen, nombre as name, '' as description, true as isActive FROM categorias")
    return jsonify(cats)

@bp.route('/api/inventory/companies/<company_cen>/categories', methods=['POST'])
def inventory_create_category(company_cen):
    data = request.get_json() or {}
    name = data.get('name')
    if not name: return jsonify({'error': 'name is required'}), 400
    new_cen = str(uuid.uuid4())
    execute("INSERT INTO categorias (cen, code, nombre) VALUES (%s, %s, %s)", (new_cen, f"CAT-{new_cen[:8]}", name))
    return jsonify({'categoryCen': new_cen, 'name': name, 'isActive': True}), 201

@bp.route('/api/inventory/companies/<company_cen>/categories/<category_cen>', methods=['PUT'])
def inventory_update_category(company_cen, category_cen):
    data = request.get_json() or {}
    name = data.get('name')
    execute("UPDATE categorias SET nombre = %s WHERE cen = %s", (name, category_cen))
    return jsonify({'categoryCen': category_cen, 'name': name, 'isActive': True})

@bp.route('/api/inventory/companies/<company_cen>/units', methods=['GET'])
def inventory_get_units(company_cen):
    units = query("SELECT cen as unitCen, nombre as name, code as abbreviation, true as isActive FROM unidades")
    return jsonify(units)

@bp.route('/api/inventory/companies/<company_cen>/units', methods=['POST'])
def inventory_create_unit(company_cen):
    data = request.get_json() or {}
    name = data.get('name')
    abbr = data.get('abbreviation')
    new_cen = str(uuid.uuid4())
    execute("INSERT INTO unidades (cen, code, nombre) VALUES (%s, %s, %s)", (new_cen, abbr or new_cen[:8], name))
    return jsonify({'unitCen': new_cen, 'name': name, 'abbreviation': abbr, 'isActive': True}), 201

@bp.route('/api/inventory/companies/<company_cen>/units/<unit_cen>', methods=['PUT'])
def inventory_update_unit(company_cen, unit_cen):
    data = request.get_json() or {}
    name = data.get('name')
    abbr = data.get('abbreviation')
    execute("UPDATE unidades SET nombre = %s, code = %s WHERE cen = %s", (name, abbr, unit_cen))
    return jsonify({'unitCen': unit_cen, 'name': name, 'abbreviation': abbr, 'isActive': True})

@bp.route('/api/inventory/companies/<company_cen>/warehouses', methods=['GET'])
def inventory_get_warehouses(company_cen):
    whs = query("SELECT cen as warehouseCen, nombre as name, activo::boolean as isActive FROM bodegas")
    return jsonify(whs)

@bp.route('/api/inventory/companies/<company_cen>/warehouses', methods=['POST'])
def inventory_create_warehouse(company_cen):
    data = request.get_json() or {}
    name = data.get('name')
    new_cen = str(uuid.uuid4())
    execute("INSERT INTO bodegas (cen, nombre, activo) VALUES (%s, %s, 1)", (new_cen, name))
    return jsonify({'warehouseCen': new_cen, 'name': name, 'isActive': True}), 201

@bp.route('/api/inventory/companies/<company_cen>/warehouses/<warehouse_cen>', methods=['PUT'])
def inventory_update_warehouse(company_cen, warehouse_cen):
    data = request.get_json() or {}
    name = data.get('name')
    active = 1 if data.get('isActive', True) else 0
    execute("UPDATE bodegas SET nombre = %s, activo = %s WHERE cen = %s", (name, active, warehouse_cen))
    return jsonify({'warehouseCen': warehouse_cen, 'name': name, 'isActive': active == 1})

# ==========================================
# 3. DOCUMENTS ENDPOINTS
# ==========================================

@bp.route('/api/inventory/companies/<company_cen>/documents', methods=['GET'])
def inventory_get_documents(company_cen):
    doc_type = request.args.get('documentType')
    docs = query("SELECT cen as documentCen, tipo as documentType, estado as status, titulo as title, creado_en as createdAt, 0 as totalItems FROM inventario.documentos WHERE 1=1")
    return jsonify(docs)

@bp.route('/api/inventory/companies/<company_cen>/documents', methods=['POST'])
def inventory_create_document(company_cen):
    data = request.get_json() or {}
    new_cen = str(uuid.uuid4())
    execute("INSERT INTO inventario.documentos (cen, tipo, titulo, estado) VALUES (%s, %s, %s, 'CONFIRMED')", 
            (new_cen, data.get('documentType', 'ADJUSTMENT'), data.get('reason', 'Manual Document')))
    return jsonify({'documentCen': new_cen, 'status': 'CONFIRMED'}), 201

@bp.route('/api/inventory/companies/<company_cen>/documents/<document_cen>', methods=['GET'])
def inventory_get_document_detail(company_cen, document_cen):
    doc = query("SELECT cen as documentCen, tipo as documentType, estado as status, titulo as title, creado_en as createdAt FROM inventario.documentos WHERE cen = %s", (document_cen,), fetch='one')
    if not doc: return jsonify({'error': 'Document not found'}), 404
    return jsonify(doc)

@bp.route('/api/inventory/companies/<company_cen>/products/<product_cen>/kardex', methods=['GET'])
def inventory_get_kardex(company_cen, product_cen):
    kardex = query("SELECT movimiento_cen as movementCen, documento_cen as documentCen, producto_cen as productCen, bodega_cen as warehouseCen, tipo_movimiento as movementType, cantidad, costo_unitario as unitCost, motivo as reason, creado_en as createdAt FROM inventario.kardex WHERE producto_cen = %s", (product_cen,))
    return jsonify(kardex)

# ==========================================
# 4. PRODUCTS & STOCK
# ==========================================

@bp.route('/api/inventory/companies/<company_cen>/dashboard', methods=['GET'])
def inventory_dashboard(company_cen):
    total_prod = query("SELECT COUNT(*) as count FROM productos", fetch='one')['count']
    total_stock = query("SELECT SUM(stock) as sum FROM productos", fetch='one')['sum'] or 0
    low_stock = query("SELECT COUNT(*) as count FROM productos WHERE stock <= 5", fetch='one')['count']
    out_stock = query("SELECT COUNT(*) as count FROM productos WHERE stock = 0", fetch='one')['count']
    return jsonify({
        'companyCen': company_cen,
        'totalProducts': int(total_prod),
        'totalStockQuantity': float(total_stock),
        'lowStockCount': int(low_stock),
        'outOfStockCount': int(out_stock)
    })

@bp.route('/api/inventory/companies/<company_cen>/products', methods=['GET'])
def inventory_get_products(company_cen):
    search = request.args.get('search')
    cat_cen = request.args.get('categoryCen')
    sql = "SELECT p.cen as productCen, p.code as sku, p.nombre as name, c.cen as categoryCen, c.nombre as categoryName, u.cen as unitCen, u.nombre as unitName, p.precio as salePrice, 0.0 as costPrice, 5.0 as reorderLevel, CASE WHEN p.activo = 1 THEN 'ACTIVE' ELSE 'INACTIVE' END as status, p.station_code as stationCode FROM productos p JOIN categorias c ON c.id = p.categoria_id JOIN unidades u ON u.id = p.unidad_id"
    prods = query(sql)
    return jsonify(prods)

@bp.route('/api/inventory/companies/<company_cen>/products', methods=['POST'])
def inventory_create_product(company_cen):
    data = request.get_json() or {}
    new_cen = str(uuid.uuid4())
    cat = query("SELECT id FROM categorias WHERE cen = %s", (data.get('categoryCen'),), fetch='one')
    uni = query("SELECT id FROM unidades WHERE cen = %s", (data.get('unitCen'),), fetch='one')
    execute("INSERT INTO productos (nombre, categoria_id, unidad_id, precio, cen, code, station_code) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (data.get('name'), cat['id'] if cat else 1, uni['id'] if uni else 1, data.get('salePrice', 10), new_cen, data.get('sku', new_cen[:8]), data.get('stationCode', 'COCINA')))
    return jsonify({'productCen': new_cen, 'sku': data.get('sku'), 'name': data.get('name'), 'status': 'ACTIVE', 'initialStock': 0.0}), 201

@bp.route('/api/inventory/companies/<company_cen>/products/<product_cen>', methods=['PUT'])
def inventory_update_product(company_cen, product_cen):
    data = request.get_json() or {}
    execute("UPDATE productos SET nombre = %s, precio = %s WHERE cen = %s", (data.get('name'), data.get('salePrice'), product_cen))
    return jsonify({'productCen': product_cen, 'name': data.get('name'), 'status': 'ACTIVE'})

@bp.route('/api/inventory/companies/<company_cen>/products/<product_cen>/status', methods=['PATCH'])
def inventory_update_product_status(company_cen, product_cen):
    data = request.get_json() or {}
    active = 1 if data.get('status') == 'ACTIVE' else 0
    execute("UPDATE productos SET activo = %s WHERE cen = %s", (active, product_cen))
    return jsonify({'productCen': product_cen, 'status': data.get('status')})

@bp.route('/api/inventory/companies/<company_cen>/products/lookup', methods=['POST'])
def inventory_lookup_products(company_cen):
    cens = request.get_json().get('productCens', [])
    prods = query("SELECT p.cen as productCen, p.code as sku, p.nombre as name, p.precio as salePrice FROM productos p WHERE p.cen = ANY(%s)", (cens,))
    return jsonify(prods)

@bp.route('/api/inventory/companies/<company_cen>/sellable-products', methods=['GET'])
def inventory_get_sellable_products(company_cen):
    prods = query("SELECT p.cen as productCen, p.nombre as name, p.precio as salePrice, p.stock::float as availableQuantity, (p.stock > 0)::boolean as isAvailable, p.station_code as stationCode FROM productos p WHERE p.activo = 1")
    return jsonify(prods)

@bp.route('/api/inventory/companies/<company_cen>/stock', methods=['GET'])
def inventory_get_stock(company_cen):
    stock = query("SELECT p.cen as productCen, p.nombre as productName, 'WH-001' as warehouseCen, 'Central' as warehouseName, p.stock::float as availableQuantity, 0.0 as reservedQuantity, u.nombre as unitName, 5.0 as reorderLevel, (p.stock <= 5)::boolean as isLowStock FROM productos p JOIN unidades u ON u.id = p.unidad_id")
    return jsonify(stock)

@bp.route('/api/inventory/companies/<company_cen>/stock/validate', methods=['POST'])
def inventory_stock_validate(company_cen):
    items = request.get_json().get('items', [])
    reqs = []
    valid = True
    for it in items:
        p = query("SELECT stock, nombre FROM productos WHERE cen = %s", (it['productCen'],), fetch='one')
        avail = float(p['stock']) if p else 0.0
        reqs.append({'productCen': it['productCen'], 'productName': p['nombre'] if p else 'N/A', 'requestedQuantity': float(it['quantity']), 'availableQuantity': avail, 'missingQuantity': max(0.0, float(it['quantity']) - avail), 'unitName': 'Units'})
        if avail < float(it['quantity']): valid = False
    return jsonify({'isValid': valid, 'requirements': reqs})

@bp.route('/api/inventory/companies/<company_cen>/stock/consume', methods=['POST'])
def inventory_stock_consume(company_cen):
    items = request.get_json().get('items', [])
    for it in items:
        execute("UPDATE productos SET stock = stock - %s WHERE cen = %s", (it['quantity'], it['productCen']))
    return jsonify({'success': True, 'documentCen': str(uuid.uuid4())})

@bp.route('/api/inventory/companies/<company_cen>/stock/increase', methods=['POST'])
def inventory_stock_increase(company_cen):
    items = request.get_json().get('items', [])
    for it in items:
        execute("UPDATE productos SET stock = stock + %s WHERE cen = %s", (it['quantity'], it['productCen']))
        p = query("SELECT nombre FROM productos WHERE cen = %s", (it['productCen'],), fetch='one')
        if p: broadcast_restock(p['nombre'], it['quantity'], company_cen)
    return jsonify("Stock increased")

@bp.route('/api/inventory/companies/<company_cen>/stock/adjustments', methods=['POST'])
def inventory_stock_adjust(company_cen):
    lines = request.get_json().get('lines', [])
    for ln in lines:
        qty = float(ln['quantity']) if ln['adjustmentType'] == 'INCREASE' else -float(ln['quantity'])
        execute("UPDATE productos SET stock = stock + %s WHERE cen = %s", (qty, ln['productCen']))
        if qty > 0:
            p = query("SELECT nombre FROM productos WHERE cen = %s", (ln['productCen'],), fetch='one')
            if p: broadcast_restock(p['nombre'], qty, company_cen)
    return jsonify({'adjustmentCen': str(uuid.uuid4()), 'status': 'CONFIRMED'}), 201

@bp.route('/api/inventory/companies/<company_cen>/restock-events', methods=['GET'])
def inventory_restock_events(company_cen):
    def event_stream():
        q = queue.Queue()
        with restock_lock: restock_queues.append(q)
        try:
            while True: yield f"data: {json.dumps(q.get())}\n\n"
        finally:
            with restock_lock: restock_queues.remove(q)
    return Response(event_stream(), mimetype="text/event-stream")
