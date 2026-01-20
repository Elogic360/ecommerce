import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { adminApi, type InventoryItem } from '../../app/api'
import type { Order, Product } from '../../app/types'
import StatCard from '../../components/admin/StatCard'
import Card from '../../components/ui/Card'
import Badge from '../../components/ui/Badge'

export default function AdminDashboardPage() {
  const [products, setProducts] = useState<Product[]>([])
  const [orders, setOrders] = useState<Order[]>([])
  const [inventory, setInventory] = useState<InventoryItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true)
        const [productsData, ordersData, inventoryData] = await Promise.all([
          adminApi.listProducts(true),
          adminApi.listOrders(),
          adminApi.listInventory()
        ])
        setProducts(productsData)
        setOrders(ordersData)
        setInventory(inventoryData)
      } catch (e) {
        console.error('Dashboard fetch error:', e)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  // Calculate stats
  const totalProducts = products.length
  const activeProducts = products.filter(p => p.is_active).length
  const lowStockCount = inventory.filter(i => i.low_stock).length
  const outOfStock = inventory.filter(i => i.stock_quantity === 0).length

  const totalOrders = orders.length
  const pendingOrders = orders.filter(o => o.order_status === 'new' || o.order_status === 'confirmed').length
  const paidOrders = orders.filter(o => o.payment_status === 'paid').length

  const totalRevenue = orders
    .filter(o => o.payment_status === 'paid')
    .reduce((sum, o) => sum + Number(o.total_amount), 0)

  const recentOrders = orders.slice(0, 5)

  return (
    <div className="space-y-6">
      {/* Stats Grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Total Revenue"
          value={loading ? '—' : `$${totalRevenue.toFixed(2)}`}
          hint="From paid orders"
        />
        <StatCard
          label="Orders"
          value={loading ? '—' : String(totalOrders)}
          hint={`${pendingOrders} pending`}
        />
        <StatCard
          label="Products"
          value={loading ? '—' : String(totalProducts)}
          hint={`${activeProducts} active`}
        />
        <StatCard
          label="Low Stock"
          value={loading ? '—' : String(lowStockCount)}
          hint={outOfStock > 0 ? `${outOfStock} out of stock` : 'All stocked'}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Recent Orders */}
        <Card>
          <div className="flex items-center justify-between mb-4">
            <div className="text-sm font-semibold">Recent Orders</div>
            <Link to="/admin/orders" className="text-xs text-indigo-400 hover:underline">
              View all →
            </Link>
          </div>
          {loading ? (
            <div className="text-sm text-slate-400">Loading…</div>
          ) : recentOrders.length === 0 ? (
            <div className="text-sm text-slate-400">No orders yet.</div>
          ) : (
            <div className="space-y-3">
              {recentOrders.map((order) => (
                <div key={order.id} className="flex items-center justify-between border-b border-white/5 pb-3 last:border-0">
                  <div>
                    <div className="font-medium">Order #{order.id}</div>
                    <div className="text-xs text-slate-400">{order.items.length} items</div>
                  </div>
                  <div className="text-right">
                    <div className="font-medium">${Number(order.total_amount).toFixed(2)}</div>
                    <Badge
                      variant={
                        order.payment_status === 'paid' ? 'success' :
                          order.payment_status === 'failed' ? 'danger' : 'warning'
                      }
                    >
                      {order.payment_status}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        {/* Quick Actions */}
        <Card>
          <div className="text-sm font-semibold mb-4">Quick Actions</div>
          <div className="grid gap-3">
            <Link
              to="/admin/products"
              className="flex items-center justify-between rounded-xl border border-white/10 bg-white/5 p-4 transition hover:bg-white/10"
            >
              <div>
                <div className="font-medium">Manage Products</div>
                <div className="text-xs text-slate-400">Add, edit, or remove products</div>
              </div>
              <span className="text-slate-400">→</span>
            </Link>
            <Link
              to="/admin/orders"
              className="flex items-center justify-between rounded-xl border border-white/10 bg-white/5 p-4 transition hover:bg-white/10"
            >
              <div>
                <div className="font-medium">Process Orders</div>
                <div className="text-xs text-slate-400">Update order & payment status</div>
              </div>
              <span className="text-slate-400">→</span>
            </Link>
            <Link
              to="/admin/inventory"
              className="flex items-center justify-between rounded-xl border border-white/10 bg-white/5 p-4 transition hover:bg-white/10"
            >
              <div>
                <div className="font-medium">Inventory Management</div>
                <div className="text-xs text-slate-400">
                  {lowStockCount > 0 ? (
                    <span className="text-amber-400">{lowStockCount} items need restocking</span>
                  ) : (
                    'Stock levels and adjustments'
                  )}
                </div>
              </div>
              <span className="text-slate-400">→</span>
            </Link>
          </div>
        </Card>
      </div>

      {/* Low Stock Alert */}
      {lowStockCount > 0 && (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2 text-amber-200">
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                <span className="font-medium">Low Stock Alert</span>
              </div>
              <div className="mt-1 text-sm text-amber-100">
                {lowStockCount} product{lowStockCount > 1 ? 's' : ''} running low on stock
              </div>
            </div>
            <Link
              to="/admin/inventory"
              className="rounded-lg bg-amber-500/20 px-3 py-1.5 text-sm font-medium text-amber-200 hover:bg-amber-500/30"
            >
              View Inventory
            </Link>
          </div>
        </div>
      )}
    </div>
  )
}