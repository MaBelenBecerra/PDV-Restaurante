from flask import Blueprint, request, jsonify
import uuid
import datetime
from database import query, execute
import inventory_client

bp = Blueprint('purchases', __name__)

@bp.route('/api/purchases/companies/<company_cen>/suppliers', methods=['GET'])
def purchases_get_suppliers(company_cen):
    suppliers = query("SELECT cen as supplierCen, nombre as name FROM proveedores")
    return jsonify(suppliers)

@bp.route('/api/purchases/companies/<company_cen>/suppliers', methods=['POST'])
def purchases_create_supplier(company_cen):
    data = request.get_json() or {}
    new_cen = str(uuid.uuid4())
    execute("INSERT INTO proveedores (cen, nombre, code) VALUES (%s, %s, %s)", (new_cen, data.get('name'), new_cen[:8]))
    return jsonify({'supplierCen': new_cen, 'name': data.get('name')}), 201

@bp.route('/api/purchases/companies/<company_cen>/suppliers/<supplier_cen>', methods=['PUT'])
def purchases_update_supplier(company_cen, supplier_cen):
    data = request.get_json() or {}
    execute("UPDATE proveedores SET nombre = %s WHERE cen = %s", (data.get('name'), supplier_cen))
    return jsonify({'supplierCen': supplier_cen, 'name': data.get('name')})

@bp.route('/api/purchases/companies/<company_cen>/orders', methods=['GET'])
def purchases_get_orders(company_cen):
    orders = query("SELECT c.cen as orderCen, p.cen as supplierCen, 'WH-001' as warehouseCen, UPPER(c.estado) as status, c.creado_en as createdAt FROM compras c JOIN proveedores p ON p.id = c.proveedor_id")
    return jsonify(orders)

@bp.route('/api/purchases/companies/<company_cen>/orders', methods=['POST'])
def purchases_create_order(company_cen):
    data = request.get_json() or {}
    sup = query("SELECT id FROM proveedores WHERE cen = %s", (data.get('supplierCen'),), fetch='one')
    order_cen = str(uuid.uuid4())
    order_id = execute("INSERT INTO compras (proveedor_id, estado, cen, code) VALUES (%s, 'pendiente', %s, %s)", (sup['id'], order_cen, order_cen[:8]))
    return jsonify({'orderCen': order_cen, 'status': 'PENDING', 'createdAt': datetime.datetime.now().isoformat()}), 201

@bp.route('/api/purchases/companies/<company_cen>/orders/<order_cen>', methods=['GET'])
def purchases_get_order_detail(company_cen, order_cen):
    order = query("SELECT c.cen as orderCen, c.estado as status, c.creado_en as createdAt, p.cen as supplierCen FROM compras c JOIN proveedores p ON p.id = c.proveedor_id WHERE c.cen = %s", (order_cen,), fetch='one')
    return jsonify(order)

@bp.route('/api/purchases/companies/<company_cen>/orders/<order_cen>', methods=['PUT'])
def purchases_update_order(company_cen, order_cen):
    return jsonify({'orderCen': order_cen, 'status': 'UPDATED'})

@bp.route('/api/purchases/companies/<company_cen>/orders/<order_cen>/receive', methods=['POST'])
def purchases_receive_order(company_cen, order_cen):
    order = query("SELECT id FROM compras WHERE cen = %s", (order_cen,), fetch='one')
    items = query("SELECT p.cen as productCen, ci.cantidad FROM compra_items ci JOIN productos p ON p.id = ci.producto_id WHERE ci.compra_id = %s", (order['id'],))
    inventory_client.increase_stock(company_cen, [{'productCen': i['productCen'], 'quantity': i['cantidad']} for i in items])
    execute("UPDATE compras SET estado = 'confirmada', confirmado_en = CURRENT_TIMESTAMP WHERE id = %s", (order['id'],))
    return jsonify({'orderCen': order_cen, 'status': 'CONFIRMED'})
