import { useEffect, useState } from 'react'
import { adminApi } from '../../app/api'
import type { Order } from '../../app/types'
import Button from '../../components/ui/Button'
import Card from '../../components/ui/Card'
import Badge from '../../components/ui/Badge'
import Modal from '../../components/ui/Modal'

const ORDER_STATUSES = ['new', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled']
const PAYMENT_STATUSES = ['pending', 'paid', 'failed', 'refunded']

export default function OrdersAdminPage() {
  const [orders, setOrders] = useState<Order[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Detail modal
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null)
  const [updating, setUpdating] = useState(false)

  const fetchOrders = async () => {
    try {
      setLoading(true)
      const data = await adminApi.listOrders()
      setOrders(data)
      setError(null)
    } catch (e: any) {
      setError(e.message || 'Failed to load orders')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchOrders()
  }, [])

  const updateStatus = async (orderId: number, orderStatus: string, paymentStatus?: string) => {
    setUpdating(true)
    try {
      const updated = await adminApi.updateOrderStatus(orderId, {
        order_status: orderStatus,
        payment_status: paymentStatus
      })
      setOrders(orders.map(o => o.id === orderId ? updated : o))
      if (selectedOrder?.id === orderId) {
        setSelectedOrder(updated)
      }
    } catch (e: any) {
      setError(e.message || 'Failed to update order')
    } finally {
      setUpdating(false)
    }
  }

  const getStatusVariant = (status: string): 'success' | 'warning' | 'danger' | 'default' => {
    switch (status) {
      case 'confirmed':
      case 'paid':
      case 'delivered':
        return 'success'
      case 'processing':
      case 'shipped':
      case 'pending':
        return 'warning'
      case 'cancelled':
      case 'failed':
        return 'danger'
      default:
        return 'default'
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold">Orders</h2>
        <p className="text-sm text-slate-400">View and manage customer orders</p>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
          {error}
        </div>
      )}

      {loading ? (
        <div className="text-sm text-slate-400">Loading orders…</div>
      ) : (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/10 text-left text-slate-400">
                  <th className="pb-3 pr-4">Order ID</th>
                  <th className="pb-3 pr-4">Customer</th>
                  <th className="pb-3 pr-4">Items</th>
                  <th className="pb-3 pr-4">Total</th>
                  <th className="pb-3 pr-4">Order Status</th>
                  <th className="pb-3 pr-4">Payment</th>
                  <th className="pb-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {orders.map((order) => (
                  <tr key={order.id} className="border-b border-white/5">
                    <td className="py-3 pr-4 font-mono">#{order.id}</td>
                    <td className="py-3 pr-4">Customer #{order.customer_id}</td>
                    <td className="py-3 pr-4">{order.items.length} items</td>
                    <td className="py-3 pr-4 font-medium">${Number(order.total_amount).toFixed(2)}</td>
                    <td className="py-3 pr-4">
                      <Badge variant={getStatusVariant(order.order_status)}>
                        {order.order_status}
                      </Badge>
                    </td>
                    <td className="py-3 pr-4">
                      <Badge variant={getStatusVariant(order.payment_status)}>
                        {order.payment_status}
                      </Badge>
                    </td>
                    <td className="py-3">
                      <Button variant="ghost" onClick={() => setSelectedOrder(order)}>
                        View
                      </Button>
                    </td>
                  </tr>
                ))}
                {orders.length === 0 && (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-slate-400">
                      No orders yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Order Detail Modal */}
      <Modal
        isOpen={!!selectedOrder}
        onClose={() => setSelectedOrder(null)}
        title={`Order #${selectedOrder?.id}`}
      >
        {selectedOrder && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <div className="text-slate-400">Customer</div>
                <div>#{selectedOrder.customer_id}</div>
              </div>
              <div>
                <div className="text-slate-400">Total</div>
                <div className="font-semibold">${Number(selectedOrder.total_amount).toFixed(2)}</div>
              </div>
            </div>

            <div>
              <div className="text-sm text-slate-400 mb-2">Items</div>
              <div className="rounded-lg border border-white/10 bg-white/5 p-3 space-y-2">
                {selectedOrder.items.map((item) => (
                  <div key={item.id} className="flex justify-between text-sm">
                    <span>Product #{item.product_id} × {item.quantity}</span>
                    <span>${(Number(item.price) * item.quantity).toFixed(2)}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-sm text-slate-400 mb-2">Order Status</div>
                <select
                  value={selectedOrder.order_status}
                  onChange={(e) => updateStatus(selectedOrder.id, e.target.value)}
                  disabled={updating}
                  className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white focus:border-indigo-400/40 focus:outline-none"
                >
                  {ORDER_STATUSES.map((s) => (
                    <option key={s} value={s} className="bg-slate-900">
                      {s}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <div className="text-sm text-slate-400 mb-2">Payment Status</div>
                <select
                  value={selectedOrder.payment_status}
                  onChange={(e) => updateStatus(selectedOrder.id, selectedOrder.order_status, e.target.value)}
                  disabled={updating}
                  className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white focus:border-indigo-400/40 focus:outline-none"
                >
                  {PAYMENT_STATUSES.map((s) => (
                    <option key={s} value={s} className="bg-slate-900">
                      {s}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="flex justify-end pt-4">
              <Button variant="secondary" onClick={() => setSelectedOrder(null)}>
                Close
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}
