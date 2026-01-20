import { useEffect, useMemo, useState } from 'react'
import { api } from '../app/api'
import type { Product } from '../app/types'
import { useCart } from '../app/store/cart'
import ProductCard from '../components/shop/ProductCard'
import Input from '../components/ui/Input'

export default function ProductsPage() {
  const add = useCart((s) => s.add)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [products, setProducts] = useState<Product[]>([])
  const [q, setQ] = useState('')

  useEffect(() => {
    let mounted = true
    setLoading(true)
    api
      .listProducts()
      .then((data) => {
        if (!mounted) return
        setProducts(data)
        setError(null)
      })
      .catch((e) => {
        if (!mounted) return
        setError(e.message || 'Failed to load products')
      })
      .finally(() => mounted && setLoading(false))

    return () => {
      mounted = false
    }
  }, [])

  const filtered = useMemo(() => {
    const query = q.trim().toLowerCase()
    if (!query) return products
    return products.filter((p) =>
      [p.name, p.description ?? '', p.category ?? ''].join(' ').toLowerCase().includes(query)
    )
  }, [products, q])

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight">Products</h2>
          <p className="mt-1 text-sm text-slate-400">Browse the catalog and add items to cart.</p>
        </div>
        <div className="w-full md:w-80">
          <div className="text-xs text-slate-400">Search</div>
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Try: sneaker, mug…" />
        </div>
      </div>

      {loading ? <div className="text-sm text-slate-400">Loading products…</div> : null}
      {error ? (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
          {error}
          <div className="mt-1 text-xs text-slate-400">
            Tip: Start the backend on port 8000 and seed products.
          </div>
        </div>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {filtered.map((p) => (
          <ProductCard key={p.id} product={p} onAdd={(prod) => add(prod, 1)} />
        ))}
      </div>

      {!loading && !error && filtered.length === 0 ? (
        <div className="text-sm text-slate-400">No products found.</div>
      ) : null}
    </div>
  )
}