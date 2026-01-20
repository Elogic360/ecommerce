import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { adminApi, getAdminToken, setAdminToken } from '../../app/api'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'

const navItems = [
  { path: '/admin', label: 'Dashboard', exact: true },
  { path: '/admin/products', label: 'Products' },
  { path: '/admin/orders', label: 'Orders' },
  { path: '/admin/customers', label: 'Customers' },
  { path: '/admin/inventory', label: 'Inventory' }
]

export default function AdminLayout() {
  const navigate = useNavigate()
  const [authenticated, setAuthenticated] = useState(false)
  const [checking, setChecking] = useState(true)
  const [tokenInput, setTokenInput] = useState('')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const checkAuth = async () => {
      const token = getAdminToken()
      if (!token) {
        setChecking(false)
        return
      }

      try {
        await adminApi.verifyAdmin()
        setAuthenticated(true)
      } catch {
        setAdminToken(null)
      } finally {
        setChecking(false)
      }
    }

    checkAuth()
  }, [])

  const handleLogin = async () => {
    setError(null)
    setAdminToken(tokenInput)

    try {
      await adminApi.verifyAdmin()
      setAuthenticated(true)
    } catch (e: any) {
      setAdminToken(null)
      setError('Invalid admin token')
    }
  }

  const handleLogout = () => {
    setAdminToken(null)
    setAuthenticated(false)
    setTokenInput('')
  }

  if (checking) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-slate-400">Checking authentication…</div>
      </div>
    )
  }

  // Login screen
  if (!authenticated) {
    return (
      <div className="mx-auto max-w-md py-20">
        <div className="rounded-2xl border border-white/10 bg-white/5 p-8 shadow-glow">
          <h1 className="text-2xl font-semibold">Admin Login</h1>
          <p className="mt-2 text-sm text-slate-400">
            Enter your admin token to access the dashboard
          </p>

          {error && (
            <div className="mt-4 rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-200">
              {error}
            </div>
          )}

          <div className="mt-6 space-y-4">
            <div>
              <div className="text-xs text-slate-400 mb-1">Admin Token</div>
              <Input
                type="password"
                value={tokenInput}
                onChange={(e) => setTokenInput(e.target.value)}
                placeholder="Enter admin token"
                onKeyDown={(e) => e.key === 'Enter' && handleLogin()}
              />
            </div>
            <Button className="w-full" onClick={handleLogin} disabled={!tokenInput}>
              Login
            </Button>
          </div>

          <div className="mt-6 text-xs text-slate-500">
            <strong>Hint:</strong> Default dev token is <code className="rounded bg-white/10 px-1">dev-admin</code>
          </div>

          <div className="mt-4 text-center">
            <Link to="/" className="text-sm text-indigo-400 hover:underline">
              ← Back to store
            </Link>
          </div>
        </div>
      </div>
    )
  }

  // Authenticated layout
  return (
    <div className="flex min-h-[calc(100vh-200px)]">
      {/* Sidebar */}
      <aside className="w-56 shrink-0 border-r border-white/10 pr-6">
        <div className="sticky top-6 space-y-6">
          <div>
            <div className="text-xs font-medium uppercase tracking-wider text-slate-500">
              Admin Panel
            </div>
          </div>

          <nav className="space-y-1">
            {navItems.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                end={item.exact}
                className={({ isActive }) =>
                  `block rounded-lg px-3 py-2 text-sm transition ${isActive
                    ? 'bg-indigo-500/20 text-white'
                    : 'text-slate-400 hover:bg-white/5 hover:text-white'
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>

          <div className="border-t border-white/10 pt-4">
            <button
              onClick={handleLogout}
              className="w-full rounded-lg px-3 py-2 text-left text-sm text-slate-400 transition hover:bg-white/5 hover:text-white"
            >
              Logout
            </button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 pl-6">
        <Outlet />
      </main>
    </div>
  )
}