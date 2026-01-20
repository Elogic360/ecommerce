import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../app/api'
import type { Order } from '../app/types'
import Badge from '../components/ui/Badge'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'

export default function OrderConfirmationPage() {
  const { id } = useParams()
  const [order, setOrder] = useState<Order | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const oid = Number(id)
    if (!oid) {
      setError('Invalid order id')
      setLoading(false)
      return
    }

    let mounted = true
    setLoading(true)
    api
      .getOrder(oid)
      .then((o) => {
        if (!mounted) return
        setOrder(o)
        setError(null)
      })
      .catch((e) => {
        if (!mounted) return
        setError(e.message || 'Failed to load order')
      })
      .finally(() => mounted && setLoading(false))

    return () => {
      mounted = false
    }
  }, [id])

  if (loading) return <div className="text-sm text-slate-400">Loading order…</div>
  if (error) {
    return (
      <div className="space-y-4">
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
          {error}
        </div>
        <Link to="/" className="text-sm text-slate-300 hover:text-white">
          ← Back home
        </Link>
      </div>
    )
  }

  if (!order) return null

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold tracking-tight">Order confirmed</h2>
        <p className="mt-1 text-sm text-slate-400">Thanks—your order is in the system.</p>
      </div>

      <Card>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="text-xs text-slate-400">Order ID</div>
            <div className="mt-1 text-lg font-semibold">#{order.id}</div>
          </div>
          <div className="flex gap-2">
            <Badge tone={order.payment_status === 'paid' ? 'success' : 'warning'}>
              Payment: {order.payment_status}
            </Badge>
            <Badge tone={order.order_status === 'paid' ? 'success' : 'neutral'}>
              Status: {order.order_status}
            </Badge>
          </div>
        </div>

        <div className="mt-5 border-t border-white/10 pt-5">
          <div className="text-sm font-semibold">Items</div>
          <div className="mt-3 space-y-2">
            {order.items.map((it) => (
              <div key={it.id} className="flex items-center justify-between text-sm text-slate-300">
                <div>
                  Product #{it.product_id} × {it.quantity}
                </div>
                <div className="font-semibold text-white">${Number(it.price).toFixed(2)}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-5 flex items-center justify-between border-t border-white/10 pt-5">
          <div className="text-sm text-slate-300">Total</div>
          <div className="text-lg font-semibold">${Number(order.total_amount).toFixed(2)}</div>
        </div>
      </Card>

      <div className="flex gap-3">
        <Link to="/products">
          <Button variant="secondary">Continue shopping</Button>
        </Link>
        <Link to="/">
          <Button variant="ghost">Home</Button>
        </Link>
      </div>
    </div>
  )
}