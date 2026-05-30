import React, { useEffect, useState } from 'react'
import Modal from '../components/Modal'
import {
  getProductos, getCategorias, getUnidades, crearProducto, editarProducto,
  toggleActivo, toggleAgotado, crearCategoria, editarCategoria,
  crearUnidad, editarUnidad, getConfiguracion, updateConfiguracion
} from '../api'

export default function Catalogo({ showToast }) {
  const [tab, setTab] = useState('productos')
  const [productos, setProductos] = useState([])
  const [categorias, setCategorias] = useState([])
  const [unidades, setUnidades] = useState([])
  const [config, setConfig] = useState({ tasa_impuesto: 0.13 })
  const [loading, setLoading] = useState(true)

  // Product filters
  const [buscar, setBuscar] = useState('')
  const [filtroCategoria, setFiltroCategoria] = useState('')
  const [filtroActivo, setFiltroActivo] = useState('todos')

  // Modals
  const [showProductoModal, setShowProductoModal] = useState(false)
  const [showCategoriaModal, setShowCategoriaModal] = useState(false)
  const [showUnidadModal, setShowUnidadModal] = useState(false)
  const [editingProducto, setEditingProducto] = useState(null)
  const [editingCategoria, setEditingCategoria] = useState(null)
  const [editingUnidad, setEditingUnidad] = useState(null)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      const [cats, units, confs] = await Promise.all([
        getCategorias(),
        getUnidades(),
        getConfiguracion()
      ])
      setCategorias(cats)
      setUnidades(units)
      setConfig(confs)
      await loadProductos()
    } catch (error) {
      showToast('error', error.message)
    } finally {
      setLoading(false)
    }
  }

  const loadProductos = async () => {
    try {
      const activo = filtroActivo === 'todos' ? null : filtroActivo === 'activo' ? 1 : 0
      const prods = await getProductos({
        categoria_id: filtroCategoria || null,
        activo: activo,
        buscar: buscar
      })
      setProductos(prods)
    } catch (error) {
      showToast('error', error.message)
    }
  }

  const handleSaveProducto = async (e) => {
    e.preventDefault()
    const formData = new FormData(e.target)
    const data = {
      nombre: formData.get('nombre'),
      categoria_id: formData.get('categoria_id'),
      unidad_id: formData.get('unidad_id'),
      precio: parseFloat(formData.get('precio')),
      stock: parseInt(formData.get('stock'))
    }

    try {
      if (editingProducto) {
        await editarProducto(editingProducto.id, data)
        showToast('success', 'Producto actualizado')
      } else {
        await crearProducto(data)
        showToast('success', 'Producto creado')
      }
      setShowProductoModal(false)
      setEditingProducto(null)
      await loadProductos()
    } catch (error) {
      showToast('error', error.message)
    }
  }

  const handleToggleActivo = async (id) => {
    try {
      await toggleActivo(id)
      showToast('success', 'Estado actualizado')
      await loadProductos()
    } catch (error) {
      showToast('error', error.message)
    }
  }

  const handleToggleAgotado = async (id) => {
    try {
      await toggleAgotado(id)
      showToast('success', 'Estado actualizado')
      await loadProductos()
    } catch (error) {
      showToast('error', error.message)
    }
  }

  const handleSaveCategoria = async (e) => {
    e.preventDefault()
    const nombre = e.target.nombre.value.trim()
    if (!nombre) return
    
    try {
      if (editingCategoria) {
        await editarCategoria(editingCategoria.id, { nombre })
      } else {
        await crearCategoria({ nombre })
      }
      showToast('success', 'Categoría guardada')
      setEditingCategoria(null)
      e.target.reset()
      const cats = await getCategorias()
      setCategorias(cats)
    } catch (error) {
      showToast('error', error.message)
    }
  }

  const handleSaveUnidad = async (e) => {
    e.preventDefault()
    const nombre = e.target.nombre.value.trim()
    if (!nombre) return
    
    try {
      if (editingUnidad) {
        await editarUnidad(editingUnidad.id, { nombre })
      } else {
        await crearUnidad({ nombre })
      }
      showToast('success', 'Unidad guardada')
      setEditingUnidad(null)
      e.target.reset()
      const units = await getUnidades()
      setUnidades(units)
    } catch (error) {
      showToast('error', error.message)
    }
  }

  const handleSaveConfig = async (e) => {
    e.preventDefault()
    const tasa = parseFloat(e.target.tasa_impuesto.value)
    try {
      await updateConfiguracion({ tasa_impuesto: tasa })
      setConfig({ tasa_impuesto: tasa })
      showToast('success', 'Configuración actualizada')
    } catch (error) {
      showToast('error', error.message)
    }
  }

  if (loading) return <div className="p-6">Cargando...</div>

  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold mb-6">Catálogo</h1>

      {/* Tabs */}
      <div className="flex space-x-4 mb-6 border-b">
        {['productos', 'categorias', 'unidades', 'configuracion'].map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 font-semibold ${
              tab === t
                ? 'border-b-2 border-blue-600 text-blue-600'
                : 'text-gray-600 hover:text-gray-800'
            }`}
          >
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {/* PRODUCTOS TAB */}
      {tab === 'productos' && (
        <div>
          <div className="mb-6 flex gap-4">
            <input
              type="text"
              placeholder="Buscar producto..."
              value={buscar}
              onChange={(e) => {
                setBuscar(e.target.value)
                loadProductos()
              }}
              className="flex-1 px-4 py-2 border rounded-lg"
            />
            <select
              value={filtroCategoria}
              onChange={(e) => {
                setFiltroCategoria(e.target.value)
                loadProductos()
              }}
              className="px-4 py-2 border rounded-lg"
            >
              <option value="">Todas las categorías</option>
              {categorias.map(c => (
                <option key={c.id} value={c.id}>{c.nombre}</option>
              ))}
            </select>
            <select
              value={filtroActivo}
              onChange={(e) => {
                setFiltroActivo(e.target.value)
                loadProductos()
              }}
              className="px-4 py-2 border rounded-lg"
            >
              <option value="todos">Todos</option>
              <option value="activo">Activo</option>
              <option value="inactivo">Inactivo</option>
            </select>
            <button
              onClick={() => {
                setEditingProducto(null)
                setShowProductoModal(true)
              }}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
            >
              + Nuevo
            </button>
          </div>

          <div className="bg-white rounded-lg shadow overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-100">
                <tr>
                  <th className="px-6 py-3 text-left font-semibold">Nombre</th>
                  <th className="px-6 py-3 text-left font-semibold">Categoría</th>
                  <th className="px-6 py-3 text-left font-semibold">Unidad</th>
                  <th className="px-6 py-3 text-right font-semibold">Precio</th>
                  <th className="px-6 py-3 text-center font-semibold">Stock</th>
                  <th className="px-6 py-3 text-center font-semibold">Estado</th>
                  <th className="px-6 py-3 text-center font-semibold">Agotado</th>
                  <th className="px-6 py-3 text-center font-semibold">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {productos.map(p => (
                  <tr key={p.id} className="border-t hover:bg-gray-50">
                    <td className="px-6 py-3">{p.nombre}</td>
                    <td className="px-6 py-3">{p.categoria}</td>
                    <td className="px-6 py-3">{p.unidad}</td>
                    <td className="px-6 py-3 text-right font-semibold">Bs. {p.precio.toFixed(2)}</td>
                    <td className="px-6 py-3 text-center">{p.stock}</td>
                    <td className="px-6 py-3 text-center">
                      <span className={`px-2 py-1 rounded text-white text-xs font-semibold ${
                        p.activo === 1 ? 'bg-green-500' : 'bg-red-500'
                      }`}>
                        {p.activo === 1 ? 'Activo' : 'Inactivo'}
                      </span>
                    </td>
                    <td className="px-6 py-3 text-center">
                      <input
                        type="checkbox"
                        checked={p.agotado === 1}
                        onChange={() => handleToggleAgotado(p.id)}
                        className="w-4 h-4 cursor-pointer"
                      />
                    </td>
                    <td className="px-6 py-3 text-center space-x-2">
                      <button
                        onClick={() => {
                          setEditingProducto(p)
                          setShowProductoModal(true)
                        }}
                        className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 text-xs"
                      >
                        Editar
                      </button>
                      <button
                        onClick={() => handleToggleActivo(p.id)}
                        className={`px-3 py-1 text-white rounded text-xs ${
                          p.activo === 1
                            ? 'bg-orange-600 hover:bg-orange-700'
                            : 'bg-green-600 hover:bg-green-700'
                        }`}
                      >
                        {p.activo === 1 ? 'Desact.' : 'Activ.'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* CATEGORIAS TAB */}
      {tab === 'categorias' && (
        <div className="max-w-2xl">
          <form onSubmit={handleSaveCategoria} className="mb-6 p-4 bg-white rounded-lg shadow">
            <div className="flex gap-2">
              <input
                type="text"
                name="nombre"
                placeholder={editingCategoria ? 'Editar categoría' : 'Nueva categoría'}
                defaultValue={editingCategoria?.nombre || ''}
                className="flex-1 px-4 py-2 border rounded-lg"
                required
              />
              <button
                type="submit"
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                {editingCategoria ? 'Guardar' : 'Crear'}
              </button>
              {editingCategoria && (
                <button
                  type="button"
                  onClick={() => setEditingCategoria(null)}
                  className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700"
                >
                  Cancelar
                </button>
              )}
            </div>
          </form>

          <div className="space-y-2">
            {categorias.map(c => (
              <div key={c.id} className="flex justify-between items-center p-4 bg-white rounded-lg shadow">
                <span className="font-semibold">{c.nombre}</span>
                <button
                  onClick={() => setEditingCategoria(c)}
                  className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm"
                >
                  Editar
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* UNIDADES TAB */}
      {tab === 'unidades' && (
        <div className="max-w-2xl">
          <form onSubmit={handleSaveUnidad} className="mb-6 p-4 bg-white rounded-lg shadow">
            <div className="flex gap-2">
              <input
                type="text"
                name="nombre"
                placeholder={editingUnidad ? 'Editar unidad' : 'Nueva unidad'}
                defaultValue={editingUnidad?.nombre || ''}
                className="flex-1 px-4 py-2 border rounded-lg"
                required
              />
              <button
                type="submit"
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                {editingUnidad ? 'Guardar' : 'Crear'}
              </button>
              {editingUnidad && (
                <button
                  type="button"
                  onClick={() => setEditingUnidad(null)}
                  className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700"
                >
                  Cancelar
                </button>
              )}
            </div>
          </form>

          <div className="space-y-2">
            {unidades.map(u => (
              <div key={u.id} className="flex justify-between items-center p-4 bg-white rounded-lg shadow">
                <span className="font-semibold">{u.nombre}</span>
                <button
                  onClick={() => setEditingUnidad(u)}
                  className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm"
                >
                  Editar
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* CONFIGURACIÓN TAB */}
      {tab === 'configuracion' && (
        <div className="max-w-2xl">
          <form onSubmit={handleSaveConfig} className="p-6 bg-white rounded-lg shadow">
            <div className="mb-6">
              <label className="block text-sm font-semibold mb-2">Tasa de Impuesto (%)</label>
              <div className="flex gap-4">
                <input
                  type="number"
                  name="tasa_impuesto"
                  step="0.01"
                  min="0"
                  max="1"
                  defaultValue={(config.tasa_impuesto * 100).toFixed(2)}
                  className="flex-1 px-4 py-2 border rounded-lg"
                  required
                />
                <span className="text-2xl font-bold text-gray-600 flex items-center">
                  {(config.tasa_impuesto * 100).toFixed(2)}%
                </span>
              </div>
            </div>
            <button
              type="submit"
              className="w-full px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-semibold"
            >
              Guardar Configuración
            </button>
          </form>
        </div>
      )}

      {/* Modal Producto */}
      <Modal
        isOpen={showProductoModal}
        title={editingProducto ? 'Editar Producto' : 'Nuevo Producto'}
        onClose={() => {
          setShowProductoModal(false)
          setEditingProducto(null)
        }}
      >
        <form onSubmit={handleSaveProducto} className="space-y-4">
          <div>
            <label className="block text-sm font-semibold mb-1">Nombre</label>
            <input
              type="text"
              name="nombre"
              defaultValue={editingProducto?.nombre || ''}
              className="w-full px-4 py-2 border rounded-lg"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-semibold mb-1">Categoría</label>
            <select
              name="categoria_id"
              defaultValue={editingProducto?.categoria_id || ''}
              className="w-full px-4 py-2 border rounded-lg"
              required
            >
              <option value="">Seleccionar</option>
              {categorias.map(c => (
                <option key={c.id} value={c.id}>{c.nombre}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-semibold mb-1">Unidad</label>
            <select
              name="unidad_id"
              defaultValue={editingProducto?.unidad_id || ''}
              className="w-full px-4 py-2 border rounded-lg"
              required
            >
              <option value="">Seleccionar</option>
              {unidades.map(u => (
                <option key={u.id} value={u.id}>{u.nombre}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-semibold mb-1">Precio</label>
            <input
              type="number"
              name="precio"
              step="0.01"
              min="0.01"
              defaultValue={editingProducto?.precio || ''}
              className="w-full px-4 py-2 border rounded-lg"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-semibold mb-1">Stock</label>
            <input
              type="number"
              name="stock"
              min="0"
              defaultValue={editingProducto?.stock || '0'}
              className="w-full px-4 py-2 border rounded-lg"
              required
            />
          </div>
          <button
            type="submit"
            className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-semibold"
          >
            Guardar
          </button>
        </form>
      </Modal>
    </div>
  )
}
