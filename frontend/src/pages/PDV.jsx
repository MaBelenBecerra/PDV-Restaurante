import React, { useEffect, useState } from 'react'
import Modal from '../components/Modal'
import {
  getTickets, crearTicket, getTicket, agregarItem, editarItem,
  eliminarItem, cancelarTicket, pagarTicket, getProductos,
  getCategorias, enviarComanda
} from '../api'

export default function PDV({ showToast }) {
  const [cuentas, setCuentas] = useState([])
  const [selectedTicketId, setSelectedTicketId] = useState(null)
  const [selectedTicket, setSelectedTicket] = useState(null)
  const [productos, setProductos] = useState([])
  const [categorias, setCategorias] = useState([])
  const [filtroCategoria, setFiltroCategoria] = useState('')
  const [buscar, setBuscar] = useState('')
  const [showNuevaCuentaModal, setShowNuevaCuentaModal] = useState(false)
  const [showPagoModal, setShowPagoModal] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadAll()
    const interval = setInterval(loadCuentas, 2000)
    return () => clearInterval(interval)
  }, [])

  const loadAll = async () => {
    try {
      setLoading(true)
      const [ctas, cats, prods] = await Promise.all([
        getTickets('abierto'),
        getCategorias(),
        getProductos()
      ])
      setCuentas(ctas)
      setCategorias(cats)
      setProductos(prods)
    } catch (error) {
      showToast('error', error.message)
    } finally {
      setLoading(false)
    }
  }

  const loadCuentas = async () => {
    try {
      const ctas = await getTickets('abierto')
      setCuentas(ctas)
    } catch (error) {
      console.error(error)
    }
  }

  const handleNuevaCuenta = async (e) => {
    e.preventDefault()
    const mesero = e.target.mesero.value.trim()
    if (!mesero) {
      showToast('error', 'El nombre del mesero es requerido')
      return
    }

    try {
      const ticket = await crearTicket({ mesero })
      setCuentas([...cuentas, ticket])
      setSelectedTicketId(ticket.id)
      setSelectedTicket(ticket)
      setShowNuevaCuentaModal(false)
      e.target.reset()
      showToast('success', 'Cuenta creada')
    } catch (error) {
      showToast('error', error.message)
    }
  }

  const handleSelectTicket = async (ticketId) => {
    try {
      const ticket = await getTicket(ticketId)
      setSelectedTicketId(ticketId)
      setSelectedTicket(ticket)
    } catch (error) {
      showToast('error', error.message)
    }
  }

  const handleAgregarProducto = async (producto) => {
    if (!selectedTicketId) {
      showToast('error', 'Selecciona una cuenta primero')
      return
    }

    try {
      const result = await agregarItem(selectedTicketId, {
        producto_id: producto.id,
        cantidad: 1
      })
      setSelectedTicket(prev => ({
        ...prev,
        items: [...(prev.items || []), result.item],
        subtotal: result.ticket_totals.subtotal,
        impuesto: result.ticket_totals.impuesto,
        total: result.ticket_totals.total
      }))
      showToast('success', 'Producto agregado')
    } catch (error) {
      showToast('error', error.message)
    }
  }

  const handleChangeQuantity = async (item, newQuantity) => {
    if (newQuantity < 1) return

    try {
      const result = await editarItem(selectedTicketId, item.id, {
        cantidad: newQuantity
      })
      setSelectedTicket(prev => ({
        ...prev,
        items: prev.items.map(i => i.id === item.id ? result.item : i),
        subtotal: result.ticket_totals.subtotal,
        impuesto: result.ticket_totals.impuesto,
        total: result.ticket_totals.total
      }))
    } catch (error) {
      showToast('error', error.message)
    }
  }

  const handleChangeNota = async (item, nota) => {
    try {
      const result = await editarItem(selectedTicketId, item.id, { nota })
      setSelectedTicket(prev => ({
        ...prev,
        items: prev.items.map(i => i.id === item.id ? result.item : i)
      }))
    } catch (error) {
      showToast('error', error.message)
    }
  }

  const handleEliminarItem = async (itemId) => {
    try {
      const result = await eliminarItem(selectedTicketId, itemId)
      setSelectedTicket(prev => ({
        ...prev,
        items: prev.items.filter(i => i.id !== itemId),
        subtotal: result.ticket_totals.subtotal,
        impuesto: result.ticket_totals.impuesto,
        total: result.ticket_totals.total
      }))
      showToast('success', 'Item eliminado')
    } catch (error) {
      showToast('error', error.message)
    }
  }

  const handleCancelar = async () => {
    if (!selectedTicketId) return
    try {
      await cancelarTicket(selectedTicketId)
      setCuentas(cuentas.filter(c => c.id !== selectedTicketId))
      setSelectedTicketId(null)
      setSelectedTicket(null)
      showToast('success', 'Cuenta cancelada')
    } catch (error) {
      showToast('error', error.message)
    }
  }

  const handleEnviarComanda = async () => {
    if (!selectedTicketId) return
    try {
      await enviarComanda(selectedTicketId)
      showToast('success', 'Comanda enviada')
    } catch (error) {
      showToast('error', error.message)
    }
  }

  const handlePagar = async (e) => {
    e.preventDefault()
    const metodo = e.target.metodo.value
    if (!metodo) {
      showToast('error', 'Selecciona un método de pago')
      return
    }

    try {
      await pagarTicket(selectedTicketId, { metodo })
      setCuentas(cuentas.filter(c => c.id !== selectedTicketId))
      setSelectedTicketId(null)
      setSelectedTicket(null)
      setShowPagoModal(false)
      showToast('success', 'Pago procesado')
    } catch (error) {
      showToast('error', error.message)
    }
  }

  const filteredProductos = productos.filter(p => {
    if (p.activo === 0 || p.agotado === 1 || p.stock === 0) return false
    if (filtroCategoria && p.categoria_id.toString() !== filtroCategoria.toString()) return false
    if (buscar && !p.nombre.toLowerCase().includes(buscar.toLowerCase())) return false
    return true
  })

  if (loading) return <div className="p-6">Cargando...</div>

  return (
    <div className="h-full flex">
      {/* Columna Izquierda - Cuentas */}
      <div className="w-80 bg-gray-900 text-white border-r border-gray-700 flex flex-col">
        <div className="p-4 border-b border-gray-700">
          <h2 className="text-xl font-bold mb-4">Cuentas Abiertas</h2>
          <button
            onClick={() => setShowNuevaCuentaModal(true)}
            className="w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 font-semibold"
          >
            + Nueva Cuenta
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          {cuentas.map(cuenta => (
            <button
              key={cuenta.id}
              onClick={() => handleSelectTicket(cuenta.id)}
              className={`w-full p-4 rounded-lg text-left transition ${
                selectedTicketId === cuenta.id
                  ? 'bg-blue-600'
                  : 'bg-gray-800 hover:bg-gray-700'
              }`}
            >
              <div className="flex justify-between items-start">
                <div>
                  <p className="font-bold text-lg">#{cuenta.id}</p>
                  <p className="text-sm text-gray-300">{cuenta.mesero}</p>
                </div>
                <div className="text-right">
                  <p className="font-bold text-lg">${cuenta.total?.toFixed(2) || '0.00'}</p>
                  <p className="text-xs text-gray-400">{new Date(cuenta.creado_en).toLocaleTimeString()}</p>
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Columna Derecha - Detalle de Cuenta */}
      <div className="flex-1 flex flex-col bg-white">
        {selectedTicket ? (
          <>
            {/* Header */}
            <div className="p-4 border-b bg-gray-100">
              <div className="flex justify-between items-center">
                <div>
                  <h3 className="text-2xl font-bold">#{selectedTicket.id}</h3>
                  <p className="text-gray-600">{selectedTicket.mesero}</p>
                </div>
                <span className={`px-4 py-2 rounded-lg font-semibold ${
                  selectedTicket.estado === 'abierto'
                    ? 'bg-blue-100 text-blue-800'
                    : 'bg-green-100 text-green-800'
                }`}>
                  {selectedTicket.estado.toUpperCase()}
                </span>
              </div>
            </div>

            {/* Selector de Productos */}
            <div className="p-4 border-b space-y-4">
              <div>
                <label className="block text-sm font-semibold mb-2">Búsqueda</label>
                <input
                  type="text"
                  placeholder="Buscar producto..."
                  value={buscar}
                  onChange={(e) => setBuscar(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg text-sm"
                />
              </div>

              <div>
                <label className="block text-sm font-semibold mb-2">Categoría</label>
                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={() => setFiltroCategoria('')}
                    className={`px-3 py-1 rounded text-sm font-semibold transition ${
                      filtroCategoria === ''
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-200 text-gray-800 hover:bg-gray-300'
                    }`}
                  >
                    Todas
                  </button>
                  {categorias.map(cat => (
                    <button
                      key={cat.id}
                      onClick={() => setFiltroCategoria(cat.id)}
                      className={`px-3 py-1 rounded text-sm font-semibold transition ${
                        filtroCategoria === cat.id
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-200 text-gray-800 hover:bg-gray-300'
                      }`}
                    >
                      {cat.nombre}
                    </button>
                  ))}
                </div>
              </div>

              {/* Grid de Productos */}
              <div className="grid grid-cols-3 gap-2 max-h-40 overflow-y-auto">
                {filteredProductos.map(prod => (
                  <button
                    key={prod.id}
                    onClick={() => handleAgregarProducto(prod)}
                    className="p-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition text-left"
                  >
                    <p className="text-sm font-semibold">{prod.nombre}</p>
                    <p className="text-lg font-bold text-green-600">${prod.precio.toFixed(2)}</p>
                    <p className="text-xs text-gray-600">Stock: {prod.stock}</p>
                  </button>
                ))}
              </div>
            </div>

            {/* Items del Ticket */}
            <div className="flex-1 overflow-y-auto p-4 border-b">
              <h4 className="font-bold mb-3">Items</h4>
              {selectedTicket.items && selectedTicket.items.length > 0 ? (
                <div className="space-y-3">
                  {selectedTicket.items.map(item => (
                    <div key={item.id} className="p-3 bg-gray-50 rounded-lg border">
                      <div className="flex justify-between items-start mb-2">
                        <div>
                          <p className="font-semibold">{item.nombre}</p>
                          <p className="text-xs text-gray-600">{item.categoria}</p>
                        </div>
                        <button
                          onClick={() => handleEliminarItem(item.id)}
                          className="text-red-600 hover:text-red-800 font-bold"
                        >
                          ✕
                        </button>
                      </div>
                      
                      <div className="flex items-center gap-2 mb-2">
                        <button
                          onClick={() => handleChangeQuantity(item, item.cantidad - 1)}
                          className="px-2 py-1 bg-gray-300 rounded hover:bg-gray-400"
                        >
                          −
                        </button>
                        <input
                          type="number"
                          value={item.cantidad}
                          onChange={(e) => handleChangeQuantity(item, parseInt(e.target.value))}
                          className="w-12 px-2 py-1 border rounded text-center"
                          min="1"
                        />
                        <button
                          onClick={() => handleChangeQuantity(item, item.cantidad + 1)}
                          className="px-2 py-1 bg-gray-300 rounded hover:bg-gray-400"
                        >
                          +
                        </button>
                        <span className="flex-1 text-right font-bold">${item.subtotal?.toFixed(2) || '0.00'}</span>
                      </div>

                      <input
                        type="text"
                        placeholder="Nota (ej: sin cebolla)"
                        value={item.nota || ''}
                        onChange={(e) => handleChangeNota(item, e.target.value)}
                        className="w-full px-2 py-1 border rounded text-sm"
                      />
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-center text-gray-500 py-8">Sin items</p>
              )}
            </div>

            {/* Totales */}
            <div className="p-4 border-b space-y-3 bg-gray-50">
              <div className="flex justify-between">
                <span className="font-semibold">Subtotal:</span>
                <span className="font-bold">${selectedTicket.subtotal?.toFixed(2) || '0.00'}</span>
              </div>
              <div className="flex justify-between">
                <span className="font-semibold">Impuesto ({(selectedTicket.tasa_impuesto * 100).toFixed(1)}%):</span>
                <span className="font-bold">${selectedTicket.impuesto?.toFixed(2) || '0.00'}</span>
              </div>
              <div className="flex justify-between text-xl bg-white p-3 rounded-lg border-2 border-blue-600">
                <span className="font-bold">TOTAL:</span>
                <span className="font-bold text-blue-600">${selectedTicket.total?.toFixed(2) || '0.00'}</span>
              </div>
            </div>

            {/* Botones de Acción */}
            <div className="p-4 space-y-2">
              <button
                onClick={handleEnviarComanda}
                className="w-full px-4 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 font-semibold"
              >
                📤 Enviar Comanda
              </button>
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={handleCancelar}
                  className="px-4 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 font-semibold"
                >
                  Cancelar
                </button>
                <button
                  onClick={() => setShowPagoModal(true)}
                  className="px-4 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 font-semibold"
                >
                  💳 Cobrar
                </button>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <p className="text-gray-500 text-xl">Selecciona una cuenta</p>
          </div>
        )}
      </div>

      {/* Modal Nueva Cuenta */}
      <Modal
        isOpen={showNuevaCuentaModal}
        title="Nueva Cuenta"
        onClose={() => setShowNuevaCuentaModal(false)}
      >
        <form onSubmit={handleNuevaCuenta} className="space-y-4">
          <div>
            <label className="block text-sm font-semibold mb-1">Nombre del Mesero</label>
            <input
              type="text"
              name="mesero"
              placeholder="Ejemplo: Carlos"
              className="w-full px-4 py-2 border rounded-lg"
              required
            />
          </div>
          <button
            type="submit"
            className="w-full px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-semibold"
          >
            Crear Cuenta
          </button>
        </form>
      </Modal>

      {/* Modal Pago */}
      <Modal
        isOpen={showPagoModal}
        title="Procesar Pago"
        onClose={() => setShowPagoModal(false)}
      >
        <form onSubmit={handlePagar} className="space-y-4">
          <div className="p-4 bg-blue-50 rounded-lg border-2 border-blue-600">
            <p className="text-sm text-gray-600">Total a pagar:</p>
            <p className="text-3xl font-bold text-blue-600">${selectedTicket?.total?.toFixed(2) || '0.00'}</p>
          </div>

          <div>
            <label className="block text-sm font-semibold mb-1">Método de Pago</label>
            <select
              name="metodo"
              className="w-full px-4 py-2 border rounded-lg"
              required
            >
              <option value="">Seleccionar método</option>
              <option value="efectivo">💵 Efectivo</option>
              <option value="qr">📱 Código QR</option>
              <option value="tarjeta">💳 Tarjeta</option>
            </select>
          </div>

          <button
            type="submit"
            className="w-full px-4 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 font-semibold text-lg"
          >
            Confirmar Pago
          </button>
        </form>
      </Modal>
    </div>
  )
}
