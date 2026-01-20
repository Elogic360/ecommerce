import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../app/api'
import { cartSubtotal, useCart } from '../app/store/cart'
import type { OrderCreate } from '../app/types'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import Input from '../components/ui/Input'

export default function CheckoutPage() {
  const nav = useNavigate()
  const lines = useCart((s) => s.lines)
  const clear = useCart((s) => s.clear)

  const subtotal = cartSubtotal(lines)

  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [method, setMethod] = useState<OrderCreate['payment_method']>('card')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const canSubmit = useMemo(() => {
    return lines.length > 0 && name.trim().length > 1 && email.trim().length > 3
  }, [lines.length, name, email])

  async function submit() {
    setError(null)
    setLoading(true)

    try {
      const payload: OrderCreate = {
        customer_name: name,
        customer_email: email,
        customer_phone: phone || undefined,
        payment_method: method,
        items: lines.map((l) => ({ product_id: l.product.id, quantity: l.quantity }))
      }

      const order = await api.createOrder(payload)

      // Mock payment verification (instant success for foundation)
      await api.verifyPayment({ order_id: order.id, success: true, provider_ref: `demo_${Date.now()}` })

      clear()
      nav(`/order/${order.id}`)
    } catch (e: any) {
      setError(e?.message || 'Checkout failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <div className="space-y-4 lg:col-span-2">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight">Checkout</h2>
          <p className="mt-1 text-sm text-slate-400">Enter details and place your order.</p>
        </div>

        {error ? (
          <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
            {error}
            <div className="mt-1 text-xs text-slate-400">
              Tip: Make sure backend is running and products have stock.
            </div>
          </div>
        ) : null}

        <Card>
          <div className="grid gap-3 md:grid-cols-2">
            <div className="md:col-span-2">
              <div className="text-xs text-slate-400">Full name</div>
              <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Jane Doe" />
            </div>
            <div>
              <div className="text-xs text-slate-400">Email</div>
              <Input
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="jane@company.com"
                type="email"
              />
            </div>
            <div>
              <div className="text-xs text-slate-400">Phone (optional)</div>
              <Input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+1 555…" />
            </div>
            <div className="md:col-span-2">
              <div className="text-xs text-slate-400">Payment method</div>
              <div className="mt-2 flex flex-wrap gap-2">
                {(['card', 'upi', 'wallet', 'cod'] as const).map((m) => (
                  <button
                    key={m}
                    type="button"
                    onClick={() => setMethod(m)}
                    className={[
                      'rounded-xl border px-3 py-2 text-sm transition',
                      method === m
                        ? 'border-indigo-400/40 bg-indigo-500/10 text-white'
                        : 'border-white/10 bg-white/5 text-slate-300 hover:bg-white/10'
                    ].join(' ')}
                  >
                    {m.toUpperCase()}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </Card>
      </div>

      <Card className="h-fit">
        <div className="text-sm font-semibold">Summary</div>
        <div className="mt-4 space-y-2 text-sm text-slate-300">
          <div className="flex justify-between">
            <span>Items</span>
            <span>{lines.reduce((n, l) => n + l.quantity, 0)}</span>
          </div>
          <div className="flex justify-between">
            <span>Subtotal</span>
            <span className="font-semibold text-white">${subtotal.toFixed(2)}</span>
          </div>
        </div>

        <div className="mt-5">
          <Button className="w-full" disabled={!canSubmit || loading} onClick={submit}>
            {loading ? 'Placing order…' : 'Place order'}
          </Button>
          <div className="mt-2 text-xs text-slate-500">
            Payments are mocked for this foundation build.
          </div>
        </div>
      </Card>
    </div>
  )
}