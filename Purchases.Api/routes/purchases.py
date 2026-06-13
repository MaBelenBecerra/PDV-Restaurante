from flask import Blueprint, request, jsonify
import uuid
import datetime
from database import query, execute

bp = Blueprint('purchases', __name__)

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

def ensure_local_product(company_cen, product_cen):
    """Check if product exists locally in PostgreSQL. If not, fetch detail from Inventory.Api and insert a stub."""
    prod = query("SELECT id, precio, nombre, code FROM productos WHERE cen = %s", (product_cen,), fetch='one')
    if prod:
        return prod
        
    # Sync from Inventory API via HTTP
    from inventory_client import lookup_products
    details = lookup_products(company_cen, [product_cen])
    if not details:
        return None
        
    d = details[0]
    cat = query("SELECT id FROM categorias LIMIT 1", fetch='one')
    cat_id = cat['id'] if cat else 1
    
    uni = query("SELECT id FROM unidades LIMIT 1", fetch='one')
    uni_id = uni['id'] if uni else 1
    
    # Insert stub product to satisfy foreign key constraints
    prod_id = execute('''
        INSERT INTO productos (nombre, categoria_id, unidad_id, precio, stock, activo, agotado, cen, code, station_code)
        VALUES (%s, %s, %s, %s, 0, 1, 0, %s, %s, %s)
    ''', (d['name'], cat_id, uni_id, d['price'], d['cen'], d['code'], d.get('stationCode', 'COCINA')))
    
    return {'id': prod_id, 'precio': d['price'], 'nombre': d['name'], 'code': d['code']}

# ==========================================
# 1. ORDERS / COMPRAS ENDPOINTS
# ==========================================

@bp.route('/api/purchases/companies/<company_cen>/orders', methods=['GET'])
def purchases_get_orders(company_cen):
    try:
        c = get_company(company_cen)
        if not c: return jsonify({'error': 'Company not found'}), 404
        
        status = request.args.get('status')
        page = request.args.get('page', '1')
        page_size = request.args.get('pageSize', '20')
        sort_descending = request.args.get('sortDescending', 'true').lower() == 'true'
        
        try:
            page = int(page)
            if page < 1: page = 1
        except ValueError:
            page = 1
            
        try:
            page_size = int(page_size)
            if page_size < 1: page_size = 20
        except ValueError:
            page_size = 20
            
        status_map_to_db = {
            'DRAFT': 'pendiente',
            'CONFIRMED': 'confirmada',
            'CANCELLED': 'cancelada'
        }
        
        where_clauses = []
        sql_params = []
        
        if status:
            db_status = status_map_to_db.get(status.upper())
            if db_status:
                where_clauses.append("c.estado = %s")
                sql_params.append(db_status)
            else:
                where_clauses.append("c.estado = %s")
                sql_params.append(status.lower())
                
        where_str = ""
        if where_clauses:
            where_str = " WHERE " + " AND ".join(where_clauses)
            
        # Count total matching records
        count_sql = "SELECT COUNT(*) as count FROM compras c JOIN proveedores p ON p.id = c.proveedor_id" + where_str
        count_res = query(count_sql, sql_params, fetch='one')
        total_count = count_res['count'] if count_res else 0
        
        # Determine sorting
        sort_dir = "DESC" if sort_descending else "ASC"
        order_by = f"ORDER BY c.fecha {sort_dir}"
        
        # Determine paging limits
        offset = (page - 1) * page_size
        
        # Final data query
        data_sql = f'''
            SELECT c.*, p.nombre as supplier_name, p.cen as supplier_cen,
                   (SELECT COUNT(*) FROM compra_items ci WHERE ci.compra_id = c.id) as item_count
            FROM compras c
            JOIN proveedores p ON p.id = c.proveedor_id
            {where_str}
            {order_by}
            LIMIT %s OFFSET %s
        '''
        
        compras = query(data_sql, sql_params + [page_size, offset])
        
        map_status = {'pendiente': 'DRAFT', 'confirmada': 'CONFIRMED', 'cancelada': 'CANCELLED'}
        
        items = [{
            'cen': r['cen'],
            'orderCen': r['cen'],
            'supplier': r['supplier_name'],
            'supplierCen': r['supplier_cen'],
            'status': map_status.get(r['estado'], 'DRAFT'),
            'date': r['fecha'].isoformat() if hasattr(r['fecha'], 'isoformat') else str(r['fecha']),
            'createdAt': r['creado_en'].isoformat() if hasattr(r['creado_en'], 'isoformat') else str(r['creado_en']),
            'confirmedAt': (r['confirmado_en'].isoformat() if hasattr(r['confirmado_en'], 'isoformat') else str(r['confirmado_en'])) if r['confirmado_en'] else None,
            'itemCount': r['item_count']
        } for r in compras]
        
        total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 1
        
        return jsonify({
            'items': items,
            'total': total_count,
            'totalCount': total_count,
            'page': page,
            'currentPage': page,
            'pageSize': page_size,
            'totalPages': total_pages
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/purchases/companies/<company_cen>/orders/<order_cen>', methods=['GET'])
def purchases_get_order_detail(company_cen, order_cen):
    try:
        c = get_company(company_cen)
        if not c: return jsonify({'error': 'Company not found'}), 404
        
        compra = query('''
            SELECT c.*, p.nombre as supplier_name, p.cen as supplier_cen
            FROM compras c
            JOIN proveedores p ON p.id = c.proveedor_id
            WHERE c.cen = %s
        ''', (order_cen,), fetch='one')
        if not compra: return jsonify({'error': 'Order not found'}), 404
        
        items = query('''
            SELECT ci.*, p.cen as product_cen, p.nombre as product_name
            FROM compra_items ci
            JOIN productos p ON p.id = ci.producto_id
            WHERE ci.compra_id = %s
            ORDER BY ci.id ASC
        ''', (compra['id'],))
        
        map_status = {'pendiente': 'DRAFT', 'confirmada': 'CONFIRMED', 'cancelada': 'CANCELLED'}
        return jsonify({
            'cen': compra['cen'],
            'supplier': compra['supplier_name'],
            'status': map_status.get(compra['estado'], 'DRAFT'),
            'date': compra['fecha'].isoformat() if hasattr(compra['fecha'], 'isoformat') else str(compra['fecha']),
            'items': [{
                'cen': row['cen'] or str(uuid.uuid4()),
                'productCen': row['product_cen'],
                'quantity': row['cantidad']
            } for row in items]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/purchases/companies/<company_cen>/orders', methods=['POST'])
def purchases_create_order(company_cen):
    try:
        c = get_company(company_cen)
        if not c: return jsonify({'error': 'Company not found'}), 404
        
        data = request.get_json() or {}
        supplier_ref = (data.get('supplierCen') or data.get('supplier') or '').strip()
        items_data = data.get('items', [])
        
        if not supplier_ref:
            return jsonify({'error': 'Supplier code or CEN is required.'}), 400
            
        prov = query("SELECT id, nombre FROM proveedores WHERE cen = %s OR UPPER(code) = %s", 
                     (supplier_ref, supplier_ref.upper()), fetch='one')
        if not prov:
            return jsonify({'error': f"Supplier '{supplier_ref}' not found."}), 400
            
        new_order_cen = str(uuid.uuid4())
        count_res = query("SELECT COUNT(*) as count FROM compras", fetch='one')
        count = count_res['count'] if count_res else 0
        new_code = f"ORD-{count+1:05d}"
        
        order_id = execute('''
            INSERT INTO compras (proveedor_id, estado, cen, code)
            VALUES (%s, 'pendiente', %s, %s)
        ''', (prov['id'], new_order_cen, new_code))
        
        total_order = 0.0
        items_created = []
        for item in items_data:
            p_cen = item.get('productCen')
            qty = item.get('quantity', 0)
            
            if not p_cen:
                continue
                
            try:
                qty_val = float(qty)
                if qty_val < 1 or qty_val != int(qty_val):
                    continue
                qty = int(qty_val)
            except (ValueError, TypeError):
                continue
                
            prod = ensure_local_product(company_cen, p_cen)
            if not prod:
                continue
                
            subtotal = float(prod['precio']) * qty
            total_order += subtotal
            new_item_cen = str(uuid.uuid4())
            
            execute('''
                INSERT INTO compra_items (compra_id, producto_id, cantidad, precio_unitario, subtotal, cen)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (order_id, prod['id'], qty, prod['precio'], subtotal, new_item_cen))
            
            items_created.append({
                'cen': new_item_cen,
                'productCen': p_cen,
                'quantity': qty
            })
            
        if not items_created:
            execute("DELETE FROM compras WHERE id = %s", (order_id,))
            return jsonify({'error': 'At least one valid item with a positive whole quantity is required.'}), 400
            
        execute("UPDATE compras SET total = %s WHERE id = %s", (total_order, order_id))
        
        return jsonify({
            'cen': new_order_cen,
            'orderCen': new_order_cen,
            'supplier': prov['nombre'],
            'status': 'DRAFT',
            'date': datetime_now_str(),
            'items': items_created
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/purchases/companies/<company_cen>/orders/<order_cen>/confirm', methods=['POST'])
@bp.route('/api/purchases/companies/<company_cen>/orders/<order_cen>/receive', methods=['POST'])
def purchases_confirm_order(company_cen, order_cen):
    try:
        c = get_company(company_cen)
        if not c: return jsonify({'error': 'Company not found'}), 404
        
        compra = query("SELECT id, estado FROM compras WHERE cen = %s", (order_cen,), fetch='one')
        if not compra: return jsonify({'error': 'Order not found'}), 404
        
        if compra['estado'] == 'confirmada':
            return jsonify({'error': 'Order is already confirmed.'}), 409
        elif compra['estado'] != 'pendiente':
            return jsonify({'error': 'Only pending orders can be confirmed.'}), 400
            
        items = query('''
            SELECT ci.cantidad, p.cen as product_cen, p.nombre
            FROM compra_items ci
            JOIN productos p ON p.id = ci.producto_id
            WHERE ci.compra_id = %s
        ''', (compra['id'],))
        
        if not items:
            return jsonify({'error': 'Order has no items.'}), 400
            
        from inventory_client import increase_stock
        for item in items:
            success = increase_stock(company_cen, item['product_cen'], item['cantidad'])
            if not success:
                return jsonify({'error': f"Failed to increase stock in inventory for {item['nombre']}"}), 400
                
        execute("UPDATE compras SET estado = 'confirmada', confirmado_en = CURRENT_TIMESTAMP WHERE cen = %s", (order_cen,))
        return purchases_get_order_detail(company_cen, order_cen)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/purchases/companies/<company_cen>/orders/<order_cen>/cancel', methods=['POST'])
def purchases_cancel_order(company_cen, order_cen):
    try:
        c = get_company(company_cen)
        if not c: return jsonify({'error': 'Company not found'}), 404
        
        compra = query("SELECT id, estado FROM compras WHERE cen = %s", (order_cen,), fetch='one')
        if not compra: return jsonify({'error': 'Order not found'}), 404
        
        if compra['estado'] == 'confirmada':
            return jsonify({'error': 'Confirmed orders cannot be cancelled.'}), 409
        elif compra['estado'] == 'cancelada':
            return jsonify({'error': 'Order is already cancelled.'}), 409
        elif compra['estado'] != 'pendiente':
            return jsonify({'error': 'Only pending orders can be cancelled.'}), 400
            
        execute("UPDATE compras SET estado = 'cancelada' WHERE cen = %s", (order_cen,))
        return purchases_get_order_detail(company_cen, order_cen)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# ==========================================
# 2. SUPPLIERS / PROVEEDORES ENDPOINTS
# ==========================================

@bp.route('/api/purchases/companies/<company_cen>/suppliers', methods=['GET'])
def purchases_get_suppliers(company_cen):
    try:
        c = get_company(company_cen)
        if not c: return jsonify({'error': 'Company not found'}), 404
        
        active_only = request.args.get('activeOnly', 'true').lower() == 'true'
        
        suppliers = query("SELECT * FROM proveedores ORDER BY nombre ASC")
        return jsonify([{
            'supplierCen': s['cen'],
            'code': s['code'],
            'name': s['nombre'],
            'active': True
        } for s in suppliers])
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/purchases/companies/<company_cen>/suppliers', methods=['POST'])
def purchases_create_supplier(company_cen):
    try:
        c = get_company(company_cen)
        if not c: return jsonify({'error': 'Company not found'}), 404
        
        data = request.get_json() or {}
        name = data.get('name', '').strip()
        code = data.get('code', '').strip()
        
        if not name: return jsonify({'error': 'Supplier name is required'}), 400
        
        exists = query("SELECT id FROM proveedores WHERE nombre = %s", (name,), fetch='one')
        if exists: return jsonify({'error': 'Supplier with this name already exists'}), 400
        
        new_cen = str(uuid.uuid4())
        if not code:
            count_res = query("SELECT COUNT(*) as count FROM proveedores", fetch='one')
            count = count_res['count'] if count_res else 0
            code = f"SUP-{count+1:05d}"
            
        execute("INSERT INTO proveedores (nombre, cen, code) VALUES (%s, %s, %s)", (name, new_cen, code))
        return jsonify({
            'supplierCen': new_cen,
            'code': code,
            'name': name,
            'active': True
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/purchases/companies/<company_cen>/suppliers/<supplier_code>', methods=['GET'])
def purchases_get_supplier(company_cen, supplier_code):
    try:
        c = get_company(company_cen)
        if not c: return jsonify({'error': 'Company not found'}), 404
        
        code = supplier_code.strip().upper()
        s = query("SELECT * FROM proveedores WHERE UPPER(code) = %s OR cen = %s", (code, supplier_code), fetch='one')
        if not s:
            return jsonify({'error': 'Supplier not found'}), 404
            
        return jsonify({
            'supplierCen': s['cen'],
            'code': s['code'],
            'name': s['nombre'],
            'active': True
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400
