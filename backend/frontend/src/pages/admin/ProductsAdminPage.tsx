import { useEffect, useState } from 'react'
import { adminApi, type ProductCreate, type ProductUpdate } from '../../app/api'
import type { Product } from '../../app/types'
import Button from '../../components/ui/Button'
import Card from '../../components/ui/Card'
import Input from '../../components/ui/Input'
import Badge from '../../components/ui/Badge'
import Modal from '../../components/ui/Modal'

type ProductFormData = {
  name: string
  description: string
  image_url: string
  price: string
  stock_quantity: string
  is_active: boolean
}

const emptyForm: ProductFormData = {
  name: '',
  description: '',
  image_url: '',
  price: '',
  stock_quantity: '0',
  is_active: true
}

export default function ProductsAdminPage() {
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Modal state
  const [showModal, setShowModal] = useState(false)
  const [editingProduct, setEditingProduct] = useState<Product | null>(null)
  const [form, setForm] = useState<ProductFormData>(emptyForm)
  const [saving, setSaving] = useState(false)

  const fetchProducts = async () => {
    try {
      setLoading(true)
      const data = await adminApi.listProducts(true)
      setProducts(data)
      setError(null)
    } catch (e: any) {
      setError(e.message || 'Failed to load products')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchProducts()
  }, [])

  const openCreateModal = () => {
    setEditingProduct(null)
    setForm(emptyForm)
    setShowModal(true)
  }

  const openEditModal = (product: Product) => {
    setEditingProduct(product)
    setForm({
      name: product.name,
      description: product.description || '',
      image_url: product.image_url || '',
      price: String(product.price),
      stock_quantity: String(product.stock_quantity),
      is_active: product.is_active
    })
    setShowModal(true)
  }

  const closeModal = () => {
    setShowModal(false)
    setEditingProduct(null)
    setForm(emptyForm)
  }

  const handleSubmit = async () => {
    setSaving(true)
    try {
      const payload: ProductCreate | ProductUpdate = {
        name: form.name,
        description: form.description || undefined,
        image_url: form.image_url || undefined,
        price: parseFloat(form.price),
        stock_quantity: parseInt(form.stock_quantity, 10),
        is_active: form.is_active
      }

      if (editingProduct) {
        await adminApi.updateProduct(editingProduct.id, payload)
      } else {
        await adminApi.createProduct(payload as ProductCreate)
      }

      closeModal()
      await fetchProducts()
    } catch (e: any) {
      setError(e.message || 'Failed to save product')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this product?')) return

    try {
      await adminApi.deleteProduct(id)
      await fetchProducts()
    } catch (e: any) {
      setError(e.message || 'Failed to delete product')
    }
  }

  const toggleActive = async (product: Product) => {
    try {
      await adminApi.updateProduct(product.id, { is_active: !product.is_active })
      await fetchProducts()
    } catch (e: any) {
      setError(e.message || 'Failed to update product')
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Products</h2>
          <p className="text-sm text-slate-400">Manage your product catalog</p>
        </div>
        <Button onClick={openCreateModal}>+ Add Product</Button>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
          {error}
        </div>
      )}

      {loading ? (
        <div className="text-sm text-slate-400">Loading products…</div>
      ) : (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/10 text-left text-slate-400">
                  <th className="pb-3 pr-4">Product</th>
                  <th className="pb-3 pr-4">Price</th>
                  <th className="pb-3 pr-4">Stock</th>
                  <th className="pb-3 pr-4">Status</th>
                  <th className="pb-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {products.map((product) => (
                  <tr key={product.id} className="border-b border-white/5">
                    <td className="py-3 pr-4">
                      <div className="flex items-center gap-3">
                        {product.image_url && (
                          <img
                            src={product.image_url}
                            alt=""
                            className="h-10 w-10 rounded-lg object-cover"
                          />
                        )}
                        <div>
                          <div className="font-medium">{product.name}</div>
                          <div className="text-xs text-slate-500 line-clamp-1">
                            {product.description || 'No description'}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="py-3 pr-4">${Number(product.price).toFixed(2)}</td>
                    <td className="py-3 pr-4">
                      <Badge variant={product.stock_quantity > 5 ? 'success' : product.stock_quantity > 0 ? 'warning' : 'danger'}>
                        {product.stock_quantity}
                      </Badge>
                    </td>
                    <td className="py-3 pr-4">
                      <button
                        onClick={() => toggleActive(product)}
                        className={`rounded-full px-2 py-0.5 text-xs ${product.is_active
                            ? 'bg-emerald-500/20 text-emerald-300'
                            : 'bg-slate-500/20 text-slate-400'
                          }`}
                      >
                        {product.is_active ? 'Active' : 'Inactive'}
                      </button>
                    </td>
                    <td className="py-3">
                      <div className="flex gap-2">
                        <Button variant="ghost" onClick={() => openEditModal(product)}>
                          Edit
                        </Button>
                        <Button variant="ghost" onClick={() => handleDelete(product.id)}>
                          Delete
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
                {products.length === 0 && (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-slate-400">
                      No products yet. Add your first product!
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Create/Edit Modal */}
      <Modal isOpen={showModal} onClose={closeModal} title={editingProduct ? 'Edit Product' : 'Add Product'}>
        <div className="space-y-4">
          <div>
            <div className="text-xs text-slate-400 mb-1">Name *</div>
            <Input
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="Product name"
            />
          </div>
          <div>
            <div className="text-xs text-slate-400 mb-1">Description</div>
            <textarea
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="Product description"
              className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder:text-slate-500 focus:border-indigo-400/40 focus:outline-none focus:ring-1 focus:ring-indigo-400/40"
              rows={3}
            />
          </div>
          <div>
            <div className="text-xs text-slate-400 mb-1">Image URL</div>
            <Input
              value={form.image_url}
              onChange={(e) => setForm({ ...form, image_url: e.target.value })}
              placeholder="https://..."
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-xs text-slate-400 mb-1">Price *</div>
              <Input
                type="number"
                value={form.price}
                onChange={(e) => setForm({ ...form, price: e.target.value })}
                placeholder="29.99"
                step="0.01"
                min="0"
              />
            </div>
            <div>
              <div className="text-xs text-slate-400 mb-1">Stock Quantity</div>
              <Input
                type="number"
                value={form.stock_quantity}
                onChange={(e) => setForm({ ...form, stock_quantity: e.target.value })}
                placeholder="0"
                min="0"
              />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="is_active"
              checked={form.is_active}
              onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
              className="rounded border-white/10 bg-white/5"
            />
            <label htmlFor="is_active" className="text-sm text-slate-300">
              Active (visible to customers)
            </label>
          </div>
          <div className="flex justify-end gap-2 pt-4">
            <Button variant="secondary" onClick={closeModal}>
              Cancel
            </Button>
            <Button onClick={handleSubmit} disabled={saving || !form.name || !form.price}>
              {saving ? 'Saving…' : editingProduct ? 'Update' : 'Create'}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
