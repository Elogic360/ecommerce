import Card from '../components/ui/Card'

export default function ContactPage() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold tracking-tight">Contact</h2>
        <p className="mt-1 text-sm text-slate-400">Add your real support details here.</p>
      </div>

      <Card>
        <div className="grid gap-3 text-sm text-slate-300">
          <div>
            <div className="text-xs text-slate-400">Email</div>
            support@example.com
          </div>
          <div>
            <div className="text-xs text-slate-400">Phone</div>
            +1 (555) 000-0000
          </div>
          <div>
            <div className="text-xs text-slate-400">Hours</div>
            Mon–Fri, 9am–5pm
          </div>
        </div>
      </Card>
    </div>
  )
}
