import { Link } from 'react-router-dom'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'

export default function HomePage() {
  return (
    <div className="space-y-10">
      <section className="relative overflow-hidden rounded-3xl border border-white/10 bg-gradient-to-br from-indigo-600/20 via-slate-950 to-fuchsia-600/10 p-8 shadow-glow md:p-12">
        <div className="max-w-2xl">
          <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-slate-300">
            Fast • Clean • Scalable
          </div>
          <h1 className="mt-4 text-3xl font-semibold tracking-tight md:text-5xl">
            A modern commerce foundation
          </h1>
          <p className="mt-4 text-slate-300 md:text-lg">
            React + Tailwind storefront, FastAPI backend, and a database-ready architecture designed
            to scale.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link to="/products">
              <Button>Browse products</Button>
            </Link>
            <Link to="/admin">
              <Button variant="secondary">Go to admin</Button>
            </Link>
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        <Card>
          <div className="text-sm font-semibold">Storefront</div>
          <div className="mt-2 text-sm text-slate-400">
            Beautiful, responsive UI for browsing products and checking out.
          </div>
        </Card>
        <Card>
          <div className="text-sm font-semibold">Admin panel</div>
          <div className="mt-2 text-sm text-slate-400">
            Manage products, orders, customers, and inventory.
          </div>
        </Card>
        <Card>
          <div className="text-sm font-semibold">Backend services</div>
          <div className="mt-2 text-sm text-slate-400">
            Product, inventory, order, payment, and customer services ready to extend.
          </div>
        </Card>
      </section>

      <section className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/[0.03] p-6 shadow-glow">
        <div>
          <div className="text-sm font-semibold">Start building</div>
          <div className="mt-1 text-sm text-slate-400">Seed the DB and see products instantly.</div>
        </div>
        <Link to="/products">
          <Button variant="ghost">View catalog</Button>
        </Link>
      </section>
    </div>
  )
}
