import Card from '../components/ui/Card'

export default function AboutPage() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold tracking-tight">About</h2>
        <p className="mt-1 text-sm text-slate-400">
          A scalable baseline architecture for an online store.
        </p>
      </div>

      <Card>
        <div className="text-sm font-semibold">What this is</div>
        <p className="mt-2 text-sm text-slate-300">
          This project is a foundation for a Shopify-style store: products, cart, checkout flow,
          orders, payments (mocked), and admin pages.
        </p>
        <div className="mt-4 text-sm text-slate-300">
          Tech:
          <ul className="mt-2 list-disc space-y-1 pl-5 text-slate-400">
            <li>React + TypeScript + Tailwind</li>
            <li>FastAPI + SQLAlchemy</li>
            <li>PostgreSQL-ready schema</li>
          </ul>
        </div>
      </Card>
    </div>
  )
}
