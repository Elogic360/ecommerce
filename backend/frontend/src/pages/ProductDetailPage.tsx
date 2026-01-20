import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../app/api'
import type { Product } from '../app/types'
import { useCart } from '../app/store/cart'
import QtyPicker from '../components/shop/QtyPicker'
import Badge from '../components/ui/Badge'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'

export default function ProductDetailPage() {
  const { id } = useParams()
  const add = useCart((s) => s.add)

  const [product, setProduct] = useState<Product | null>(null)
  const [qty, setQty] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const pid = Number(id)
    if (!pid) {
      setError('Invalid product id')
      setLoading(false)
      return
    }

    let mounted = true
    setLoading(true)
    api
      .getProduct(pid)
      .then((p) => {
        if (!mounted) return
        setProduct(p)
        setError(null)
      })
      .catch((e) => {
        if (!mounted) return
        setError(e.message || 'Failed to load product')
      })
      .finally(() => mounted && setLoading(false))

    return () => {
      mounted = false
    }
  }, [id])

  if (loading) return <div className="text-sm text-slate-400">Loading…</div>
  if (error) {
    return (
      <div className="space-y-4">
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
          {error}
        </div>
        <Link to="/products" className="text-sm text-slate-300 hover:text-white">
          ← Back to products
        </Link>
      </div>
    )
  }

  if (!product) return null

  const inStock = product.stock_quantity > 0

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Card className="overflow-hidden p-0">
        <div className="relative aspect-[4/3]">
          <img
            src={product.image_url || 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=1200&q=80'}
            alt={product.name}
            className="h-full w-full object-cover"
          />
          <div className="absolute left-4 top-4">
            <Badge tone={inStock ? 'success' : 'warning'}>{inStock ? 'In stock' : 'Sold out'}</Badge>
          </div>
        </div>
      </Card>

      <div className="space-y-5">
        <div>
          <div className="text-xs text-slate-400">{product.category || 'General'}</div>
          <h1 className="mt-1 text-3xl font-semibold tracking-tight">{product.name}</h1>
          <div className="mt-3 text-lg font-semibold">${Number(product.price).toFixed(2)}</div>
        </div>

        <p className="text-slate-300">
          {product.description ||
            'A thoughtfully designed product. Extend this description with rich content later.'}
        </p>

        <div className="flex flex-wrap items-center gap-3">
          <QtyPicker value={qty} onChange={setQty} max={product.stock_quantity || 1} />
          <Button disabled={!inStock} onClick={() => add(product, qty)}>
            Add to cart
          </Button>
          <Link to="/cart">
            <Button variant="secondary">Go to cart</Button>
          </Link>
        </div>

        <div className="text-xs text-slate-400">
          Stock: <span className="text-slate-200">{product.stock_quantity}</span>
        </div>

        <Link to="/products" className="text-sm text-slate-300 hover:text-white">
          ← Back to products
        </Link>
      </div>
    </div>
  )
}