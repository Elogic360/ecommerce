import { useEffect, useState } from 'react'
import { adminApi, type Customer } from '../../app/api'
import Card from '../../components/ui/Card'
import Badge from '../../components/ui/Badge'

export default function CustomersAdminPage() {
  const [customers, setCustomers] = useState<Customer[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchCustomers = async () => {
      try {
        setLoading(true)
        const data = await adminApi.listCustomers()
        setCustomers(data)
        setError(null)
      } catch (e: any) {
        setError(e.message || 'Failed to load customers')
      } finally {
        setLoading(false)
      }
    }

    fetchCustomers()
  }, [])

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Customers</h2>
          <p className="text-sm text-slate-400">View your customer base</p>
        </div>
        <Badge variant="default">{customers.length} total</Badge>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
          {error}
        </div>
      )}

      {loading ? (
        <div className="text-sm text-slate-400">Loading customers…</div>
      ) : (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/10 text-left text-slate-400">
                  <th className="pb-3 pr-4">ID</th>
                  <th className="pb-3 pr-4">Name</th>
                  <th className="pb-3 pr-4">Email</th>
                  <th className="pb-3">Phone</th>
                </tr>
              </thead>
              <tbody>
                {customers.map((customer) => (
                  <tr key={customer.id} className="border-b border-white/5">
                    <td className="py-3 pr-4 font-mono text-slate-400">#{customer.id}</td>
                    <td className="py-3 pr-4 font-medium">{customer.name}</td>
                    <td className="py-3 pr-4">
                      <a
                        href={`mailto:${customer.email}`}
                        className="text-indigo-400 hover:underline"
                      >
                        {customer.email}
                      </a>
                    </td>
                    <td className="py-3 text-slate-400">
                      {customer.phone || '—'}
                    </td>
                  </tr>
                ))}
                {customers.length === 0 && (
                  <tr>
                    <td colSpan={4} className="py-8 text-center text-slate-400">
                      No customers yet. They'll appear here after their first order.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  )
}
