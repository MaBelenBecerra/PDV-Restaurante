import React, { useEffect, useState } from 'react'
import Modal from '../components/Modal'
import { getInventario, ajustarStock } from '../api'

export default function Inventario({ showToast }) {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [editingItem, setEditingItem] = useState(null)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      const data = await getInventario()
      setItems(data)
    } catch (error) {
      showToast('error', error.message)
    } finally {
      setLoading(false)
    }
  }

  const handleAjuste = async (e) => {
    e.preventDefault()
    const formData = new FormData(e.target)
    const data = {
      producto_id: formData.get('producto_id'),
      tipo: formData.get('tipo'),
      cantidad: parseInt(formData.get('cantidad')),
      motivo: formData.get('motivo')
    }

    try {
      await ajustarStock(data)
      showToast('success', 'Stock ajustado')
      setShowModal(false)
      setEditingItem(null)
      await loadData()
    } catch (error) {
      showToast('error', error.message)
    }
  }

  const getEstadoBadge = (estado) => {
    const badges = {
      'ok': 'bg-green-100 text-green-800',
      'bajo': 'bg-yellow-100 text-yellow-800',
      'agotado': 'bg-red-100 text-red-800'
    }
    return badges[estado] || 'bg-gray-100 text-gray-800'
  }

  const getEstadoLabel = (estado) => {
    const labels = {
      'ok': 'OK',
      'bajo': 'BAJO',
      'agotado': 'AGOTADO'
    }
    return labels[estado] || estado
  }

  if (loading) return <div className="p-6">Cargando...</div>

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Inventario</h1>
        <button
          onClick={loadData}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          ↻ Actualizar
        </button>
      </div>

      <div className="bg-white rounded-lg shadow overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-100">
            <tr>
              <th className="px-6 py-3 text-left font-semibold">Producto</th>
              <th className="px-6 py-3 text-left font-semibold">Categoría</th>
              <th className="px-6 py-3 text-left font-semibold">Unidad</th>
              <th className="px-6 py-3 text-center font-semibold">Stock</th>
              <th className="px-6 py-3 text-center font-semibold">Estado</th>
              <th className="px-6 py-3 text-right font-semibold">Precio</th>
              <th className="px-6 py-3 text-center font-semibold">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {items.map(item => (
              <tr key={item.id} className="border-t hover:bg-gray-50">
                <td className="px-6 py-3 font-semibold">{item.nombre}</td>
                <td className="px-6 py-3">{item.categoria}</td>
                <td className="px-6 py-3">{item.unidad}</td>
                <td className="px-6 py-3 text-center font-semibold text-lg">{item.stock}</td>
                <td className="px-6 py-3 text-center">
                  <span className={`px-3 py-1 rounded-full text-xs font-bold ${getEstadoBadge(item.estado)}`}>
                    {getEstadoLabel(item.estado)}
                  </span>
                </td>
                <td className="px-6 py-3 text-right">${item.precio.toFixed(2)}</td>
                <td className="px-6 py-3 text-center">
                  <button
                    onClick={() => {
                      setEditingItem(item)
                      setShowModal(true)
                    }}
                    className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm"
                  >
                    Ajustar
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Modal Ajuste */}
      <Modal
        isOpen={showModal}
        title={`Ajustar Stock - ${editingItem?.nombre || ''}`}
        onClose={() => {
          setShowModal(false)
          setEditingItem(null)
        }}
      >
        <form onSubmit={handleAjuste} className="space-y-4">
          <input
            type="hidden"
            name="producto_id"
            value={editingItem?.id || ''}
          />
          
          <div>
            <label className="block text-sm font-semibold mb-1">Tipo de Movimiento</label>
            <select
              name="tipo"
              className="w-full px-4 py-2 border rounded-lg"
              required
            >
              <option value="">Seleccionar</option>
              <option value="entrada">Entrada (Compra/Devolución)</option>
              <option value="salida">Salida (Ajuste/Merma)</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-semibold mb-1">Cantidad</label>
            <input
              type="number"
              name="cantidad"
              min="1"
              className="w-full px-4 py-2 border rounded-lg"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-semibold mb-1">Motivo</label>
            <textarea
              name="motivo"
              rows="3"
              placeholder="Ejemplo: Próxima entrega del proveedor"
              className="w-full px-4 py-2 border rounded-lg"
              required
            />
          </div>

          <button
            type="submit"
            className="w-full px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-semibold"
          >
            Guardar Ajuste
          </button>
        </form>
      </Modal>
    </div>
  )
}
