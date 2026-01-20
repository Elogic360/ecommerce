import { Link, useNavigate } from 'react-router-dom'
import { cartSubtotal, useCart } from '../app/store/cart'
import QtyPicker from '../components/shop/QtyPicker'
import Badge from '../components/ui/Badge'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'

export default function CartPage() {
  const nav = useNavigate()
  const lines = useCart((s) => s.lines)
  const setQty = useCart((s) => s.setQty)
  const remove = useCart((s) => s.remove)

  const subtotal = cartSubtotal(lines)

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight">Cart</h2>
          <p className="mt-1 text-sm text-slate-400">Review items before checkout.</p>
        </div>
        <Link to="/products" className="text-sm text-slate-300 hover:text-white">
          Continue shopping
        </Link>
      </div>

      {lines.length === 0 ? (
        <Card>
          <div className="text-sm">Your cart is empty.</div>
          <div className="mt-4">
            <Link to="/products">
              <Button>Browse products</Button>
            </Link>
          </div>
        </Card>
      ) : (
        <div className="grid gap-4 lg:grid-cols-3">
          <div className="space-y-3 lg:col-span-2">
            {lines.map((l) => (
              <Card key={l.product.id} className="flex flex-col gap-4 md:flex-row md:items-center">
                <div className="flex flex-1 items-center gap-4">
                  <img
                    src={l.product.image_url || 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=1200&q=80'}
                    alt={l.product.name}
                    className="h-16 w-16 rounded-xl object-cover"
                  />
                  <div>
                    <div className="text-sm font-semibold">{l.product.name}</div>
                    <div className="mt-1 text-xs text-slate-400">
                      ${Number(l.product.price).toFixed(2)} •{' '}
                      <Badge tone={l.product.stock_quantity > 0 ? 'success' : 'warning'}>
                        {l.product.stock_quantity > 0 ? 'Available' : 'Sold out'}
                      </Badge>
                    </div>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-3">
                  <QtyPicker
                    value={l.quantity}
                    onChange={(n) => setQty(l.product.id, n)}
                    max={Math.max(1, l.product.stock_quantity)}
                  />
                  <Button variant="ghost" onClick={() => remove(l.product.id)}>
                    Remove
                  </Button>
                </div>
              </Card>
            ))}
          </div>

          <Card className="h-fit">
            <div className="text-sm font-semibold">Order summary</div>
            <div className="mt-4 flex items-center justify-between text-sm text-slate-300">
              <span>Subtotal</span>
              <span className="font-semibold text-white">${subtotal.toFixed(2)}</span>
            </div>
            <div className="mt-2 text-xs text-slate-500">Taxes/shipping calculated later.</div>
            <div className="mt-5 flex gap-3">
              <Button className="w-full" onClick={() => nav('/checkout')}>
                Checkout
              </Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  )
}