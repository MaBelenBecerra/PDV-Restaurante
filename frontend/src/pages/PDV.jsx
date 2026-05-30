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

    const itemsExistentes = selectedTicket.items || []
    const existingItem = itemsExistentes.find(item => item.producto_id === producto.id)

    try {
      if (existingItem) {
        const newQty = existingItem.cantidad + 1
        const result = await editarItem(selectedTicketId, existingItem.id, {
          cantidad: newQty
        })
        setSelectedTicket(prev => ({
          ...prev,
          items: prev.items.map(i => i.id === existingItem.id ? result.item : i),
          subtotal: result.ticket_totals.subtotal,
          impuesto: result.ticket_totals.impuesto,
          total: result.ticket_totals.total
        }))
        showToast('success', 'Cantidad incrementada')
      } else {
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
      }
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
    <div className="h-full flex bg-gray-100 font-sans">
      {/* Columna Izquierda - Cuentas */}
      <div className="w-80 bg-gray-955 text-white border-r border-gray-800 flex flex-col shadow-xl" style={{ backgroundColor: '#111827' }}>
        <div className="p-5 border-b border-gray-800 bg-gray-900/50 backdrop-blur-md sticky top-0 z-10">
          <h2 className="text-lg font-bold tracking-wide mb-4 text-gray-100 flex items-center gap-2">
            <span>📋</span> Cuentas Abiertas
          </h2>
          <button
            onClick={() => setShowNuevaCuentaModal(true)}
            className="w-full px-4 py-3 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl shadow-lg shadow-emerald-950/20 hover:shadow-emerald-500/10 active:scale-[0.98] transition-all font-semibold flex items-center justify-center gap-2"
          >
            <span className="text-lg">+</span> Nueva Cuenta
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-3 scrollbar-thin scrollbar-thumb-gray-800">
          {cuentas.map(cuenta => (
            <button
              key={cuenta.id}
              onClick={() => handleSelectTicket(cuenta.id)}
              className={`w-full p-4 rounded-xl text-left border transition-all duration-200 group relative overflow-hidden ${
                selectedTicketId === cuenta.id
                  ? 'bg-blue-600 border-blue-500 text-white shadow-lg shadow-blue-900/30'
                  : 'bg-gray-900/50 hover:bg-gray-800/80 border-gray-800 hover:border-gray-700 text-gray-300'
              }`}
            >
              {/* Highlight bar */}
              {selectedTicketId === cuenta.id && (
                <div className="absolute left-0 top-0 bottom-0 w-1 bg-white rounded-r-md"></div>
              )}
              
              <div className="flex justify-between items-start gap-2">
                <div className="min-w-0 flex-1">
                  <p className={`font-bold text-sm tracking-wide truncate ${selectedTicketId === cuenta.id ? 'text-white' : 'text-gray-100'}`}>
                    👤 {cuenta.mesero}
                  </p>
                  <p className={`text-xs mt-1 font-mono ${selectedTicketId === cuenta.id ? 'text-blue-200' : 'text-gray-500'}`}>
                    ID: {cuenta.id.substring(0, 8)}...
                  </p>
                </div>
                <div className="text-right flex-shrink-0">
                  <p className={`font-black text-sm ${selectedTicketId === cuenta.id ? 'text-white' : 'text-emerald-400'}`}>
                    Bs. {cuenta.total?.toFixed(2) || '0.00'}
                  </p>
                  <p className={`text-[10px] mt-1 ${selectedTicketId === cuenta.id ? 'text-blue-200' : 'text-gray-500'}`}>
                    ⏰ {new Date(cuenta.creado_en).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </p>
                </div>
              </div>
            </button>
          ))}
          {cuentas.length === 0 && (
            <div className="text-center text-gray-500 py-12">
              <span className="text-3xl block mb-2">🍽️</span>
              <p className="text-sm">No hay cuentas abiertas</p>
            </div>
          )}
        </div>
      </div>

      {/* Columna Derecha / Principal */}
      <div className="flex-1 flex bg-gray-50 overflow-hidden">
        {selectedTicket ? (
          <div className="flex-1 flex h-full overflow-hidden">
            {/* PANEL CENTRAL: Catálogo de Productos */}
            <div className="flex-1 flex flex-col bg-gray-50 border-r border-gray-200 overflow-hidden h-full">
              {/* Buscador y Categorías */}
              <div className="p-5 bg-white border-b border-gray-200 space-y-4 shadow-sm z-10">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <h3 className="text-base font-bold text-gray-800 tracking-tight uppercase flex items-center gap-2">
                    <span>🛍️</span> Catálogo de Productos
                  </h3>
                  <div className="relative w-full sm:w-72">
                    <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-400">
                      🔍
                    </span>
                    <input
                      type="text"
                      placeholder="Buscar producto..."
                      value={buscar}
                      onChange={(e) => setBuscar(e.target.value)}
                      className="w-full pl-9 pr-4 py-2 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all placeholder-gray-400 bg-gray-50 focus:bg-white"
                    />
                  </div>
                </div>

                {/* Categorías (Pills) */}
                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={() => setFiltroCategoria('')}
                    className={`px-4 py-2 rounded-full text-xs font-semibold tracking-wide transition-all ${
                      filtroCategoria === ''
                        ? 'bg-blue-600 text-white shadow-md shadow-blue-500/10'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200 hover:text-gray-800'
                    }`}
                  >
                    Todas
                  </button>
                  {categorias.map(cat => (
                    <button
                      key={cat.id}
                      onClick={() => setFiltroCategoria(cat.id)}
                      className={`px-4 py-2 rounded-full text-xs font-semibold tracking-wide transition-all ${
                        filtroCategoria === cat.id
                          ? 'bg-blue-600 text-white shadow-md shadow-blue-500/10'
                          : 'bg-gray-100 text-gray-600 hover:bg-gray-200 hover:text-gray-800'
                      }`}
                    >
                      {cat.nombre}
                    </button>
                  ))}
                </div>
              </div>

              {/* Grid de Productos - Ocupa todo el alto de forma scrollable */}
              <div className="flex-1 overflow-y-auto p-5 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-4 h-full scrollbar-thin">
                {filteredProductos.map(prod => (
                  <button
                    key={prod.id}
                    onClick={() => handleAgregarProducto(prod)}
                    className="flex flex-col justify-between p-4 bg-white hover:bg-blue-50/5 hover:-translate-y-1 hover:shadow-lg hover:shadow-gray-200/50 border border-gray-100 rounded-2xl transition-all duration-200 text-left group relative active:scale-[0.98]"
                  >
                    <div className="space-y-1.5">
                      <p className="font-bold text-gray-800 text-sm group-hover:text-blue-600 transition-colors line-clamp-2">
                        {prod.nombre}
                      </p>
                      <p className="text-[10px] text-gray-400 font-semibold tracking-wider uppercase">
                        {categorias.find(c => c.id === prod.categoria_id)?.nombre || 'General'}
                      </p>
                    </div>
                    <div className="mt-4 flex justify-between items-end">
                      <span className="text-base font-black text-blue-600">
                        Bs. {prod.precio.toFixed(2)}
                      </span>
                      <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase ${
                        prod.stock > 5
                          ? 'bg-emerald-50 text-emerald-700'
                          : prod.stock > 0
                          ? 'bg-amber-50 text-amber-700'
                          : 'bg-rose-50 text-rose-700'
                      }`}>
                        Stock: {prod.stock}
                      </span>
                    </div>
                  </button>
                ))}
                {filteredProductos.length === 0 && (
                  <div className="col-span-full flex flex-col items-center justify-center py-20 text-gray-400">
                    <span className="text-4xl mb-3">🔍</span>
                    <p className="text-base font-medium">No se encontraron productos disponibles</p>
                    <p className="text-xs text-gray-500 mt-1">Intenta ajustando el filtro o el término de búsqueda.</p>
                  </div>
                )}
              </div>
            </div>

            {/* PANEL DERECHO: Detalle del Ticket y Carrito de Items */}
            <div className="w-[400px] bg-white flex flex-col shadow-2xl z-20 border-l border-gray-200 h-full overflow-hidden">
              {/* Header de la Cuenta */}
              <div className="p-5 border-b border-gray-200 bg-gray-50 flex justify-between items-center flex-shrink-0">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-[10px] text-gray-400 font-bold uppercase tracking-wider">Orden activa</span>
                    <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-wider ${
                      selectedTicket.estado === 'abierto'
                        ? 'bg-blue-100 text-blue-800'
                        : 'bg-emerald-100 text-emerald-800'
                    }`}>
                      {selectedTicket.estado}
                    </span>
                  </div>
                  <h3 className="text-lg font-black text-gray-800 truncate" title={selectedTicket.id}>
                    #{selectedTicket.id.substring(0, 8)}...
                  </h3>
                  <p className="text-xs text-gray-500 mt-0.5 flex items-center gap-1">
                    <span>👤</span> Mesero: <strong className="text-gray-700 font-semibold">{selectedTicket.mesero}</strong>
                  </p>
                </div>
              </div>

              {/* Items del Ticket - Con espacio vertical maximizado y scrollable */}
              <div className="flex-1 overflow-y-auto p-5 space-y-4 bg-gray-50/30 scrollbar-thin">
                <h4 className="font-bold text-gray-500 text-xs tracking-wider uppercase mb-1">Items en Comanda</h4>
                {selectedTicket.items && selectedTicket.items.length > 0 ? (
                  <div className="space-y-3">
                    {selectedTicket.items.map(item => (
                      <div key={item.id} className="p-4 bg-white rounded-2xl border border-gray-100 shadow-sm hover:shadow-md transition-shadow">
                        <div className="flex justify-between items-start mb-3 gap-2">
                          <div className="min-w-0">
                            <p className="font-bold text-gray-800 text-sm truncate">{item.nombre}</p>
                            <p className="text-[10px] text-gray-400 font-semibold uppercase mt-0.5">{item.categoria}</p>
                          </div>
                          <button
                            onClick={() => handleEliminarItem(item.id)}
                            className="p-1 hover:bg-rose-50 text-gray-400 hover:text-rose-600 rounded-lg transition-colors text-xs flex-shrink-0"
                            title="Eliminar item"
                          >
                            ✕
                          </button>
                        </div>
                        
                        <div className="flex items-center justify-between gap-4 mt-2">
                          <div className="flex items-center gap-1 bg-gray-100 p-0.5 rounded-lg">
                            <button
                              onClick={() => handleChangeQuantity(item, item.cantidad - 1)}
                              className="w-7 h-7 flex items-center justify-center bg-white hover:bg-gray-50 text-gray-600 font-bold rounded-md shadow-sm transition-all active:scale-95"
                            >
                              −
                            </button>
                            <input
                              type="number"
                              value={item.cantidad}
                              onChange={(e) => handleChangeQuantity(item, parseInt(e.target.value) || 1)}
                              className="w-10 text-center bg-transparent border-0 font-bold text-sm text-gray-800 focus:outline-none"
                              min="1"
                            />
                            <button
                              onClick={() => handleChangeQuantity(item, item.cantidad + 1)}
                              className="w-7 h-7 flex items-center justify-center bg-white hover:bg-gray-50 text-gray-600 font-bold rounded-md shadow-sm transition-all active:scale-95"
                            >
                              +
                            </button>
                          </div>
                          <span className="font-extrabold text-sm text-gray-900">
                            Bs. {item.subtotal?.toFixed(2) || '0.00'}
                          </span>
                        </div>

                        <div className="mt-3">
                          <input
                            type="text"
                            placeholder="Añadir nota especial..."
                            value={item.nota || ''}
                            onChange={(e) => handleChangeNota(item, e.target.value)}
                            className="w-full px-3 py-1.5 border border-gray-150 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-blue-500 bg-gray-50 focus:bg-white placeholder-gray-400 transition-all"
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center py-20 text-gray-400 border-2 border-dashed border-gray-200 rounded-2xl bg-white p-5">
                    <span className="text-4xl mb-2">🛒</span>
                    <p className="text-sm font-semibold">El pedido está vacío</p>
                    <p className="text-xs text-gray-500 text-center mt-1">Selecciona productos de la izquierda para agregarlos.</p>
                  </div>
                )}
              </div>

              {/* Totales */}
              <div className="p-5 border-t border-gray-200 bg-white space-y-3 flex-shrink-0 shadow-[0_-4px_12px_rgba(0,0,0,0.03)] z-10">
                <div className="flex justify-between text-sm text-gray-600">
                  <span className="font-semibold">Subtotal:</span>
                  <span className="font-bold text-gray-800">Bs. {selectedTicket.subtotal?.toFixed(2) || '0.00'}</span>
                </div>
                <div className="flex justify-between text-sm text-gray-600">
                  <span className="font-semibold">Impuesto ({((selectedTicket.tasa_impuesto || 0.13) * 100).toFixed(1)}%):</span>
                  <span className="font-bold text-gray-800">Bs. {selectedTicket.impuesto?.toFixed(2) || '0.00'}</span>
                </div>
                <div className="flex justify-between text-lg bg-blue-50/50 p-4 rounded-xl border border-blue-100">
                  <span className="font-black text-gray-800 text-base">TOTAL:</span>
                  <span className="font-black text-blue-600 text-lg">Bs. {selectedTicket.total?.toFixed(2) || '0.00'}</span>
                </div>
              </div>

              {/* Botones de Acción */}
              <div className="p-5 bg-white border-t border-gray-100 space-y-2.5 flex-shrink-0 z-10">
                <button
                  onClick={handleEnviarComanda}
                  className="w-full px-4 py-3 bg-violet-600 hover:bg-violet-500 text-white rounded-xl font-bold active:scale-[0.98] transition-all shadow-md shadow-violet-500/10 flex items-center justify-center gap-2"
                >
                  <span>📤</span> Enviar Comanda
                </button>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    onClick={handleCancelar}
                    className="px-4 py-3 bg-gray-100 hover:bg-rose-50 text-gray-600 hover:text-rose-600 rounded-xl font-bold active:scale-[0.98] transition-all border border-gray-200 hover:border-rose-100 flex items-center justify-center gap-1.5"
                  >
                    <span>✕</span> Cancelar
                  </button>
                  <button
                    onClick={() => setShowPagoModal(true)}
                    className="px-4 py-3 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl font-bold active:scale-[0.98] transition-all shadow-md shadow-emerald-500/10 flex items-center justify-center gap-1.5"
                  >
                    <span>💳</span> Cobrar
                  </button>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center py-20 text-gray-400 bg-white h-full border-r border-gray-200">
            <span className="text-5xl mb-4 animate-bounce">👈</span>
            <p className="text-xl font-black text-gray-700">Comienza seleccionando una cuenta</p>
            <p className="text-sm text-gray-500 mt-1 max-w-xs text-center">Selecciona una de las cuentas abiertas en el panel izquierdo o crea una nueva cuenta.</p>
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
            <p className="text-3xl font-bold text-blue-600">Bs. {selectedTicket?.total?.toFixed(2) || '0.00'}</p>
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
