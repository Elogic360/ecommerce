import { Link, NavLink } from 'react-router-dom'
import { useCart } from '../../app/store/cart'
import Badge from '../ui/Badge'

function cx(isActive: boolean) {
  return [
    'rounded-lg px-3 py-2 text-sm transition',
    isActive
      ? 'bg-white/10 text-white shadow-glow'
      : 'text-slate-300 hover:text-white hover:bg-white/5'
  ].join(' ')
}

export default function NavBar() {
  const lines = useCart((s) => s.lines)
  const count = lines.reduce((n, l) => n + l.quantity, 0)

  return (
    <header className="sticky top-0 z-50 border-b border-white/10 bg-slate-950/80 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
        <Link to="/" className="flex items-center gap-2">
          <div className="h-9 w-9 rounded-xl bg-gradient-to-br from-indigo-500 via-fuchsia-500 to-amber-400 shadow-glow" />
          <div className="leading-tight">
            <div className="text-sm font-semibold">Vibe Store</div>
            <div className="text-xs text-slate-400">Modern commerce foundation</div>
          </div>
        </Link>

        <nav className="hidden items-center gap-1 md:flex">
          <NavLink to="/products" className={({ isActive }) => cx(isActive)}>
            Products
          </NavLink>
          <NavLink to="/about" className={({ isActive }) => cx(isActive)}>
            About
          </NavLink>
          <NavLink to="/contact" className={({ isActive }) => cx(isActive)}>
            Contact
          </NavLink>
          <NavLink to="/policies" className={({ isActive }) => cx(isActive)}>
            Policies
          </NavLink>
          <NavLink to="/admin" className={({ isActive }) => cx(isActive)}>
            Admin
          </NavLink>
        </nav>

        <div className="flex items-center gap-3">
          <Link
            to="/cart"
            className="group relative rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-200 shadow-glow transition hover:bg-white/10"
          >
            Cart
            {count > 0 && (
              <span className="ml-2">
                <Badge>{count}</Badge>
              </span>
            )}
          </Link>
        </div>
      </div>
    </header>
  )
}