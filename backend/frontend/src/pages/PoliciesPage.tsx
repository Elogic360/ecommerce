import Card from '../components/ui/Card'

export default function PoliciesPage() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold tracking-tight">Policies</h2>
        <p className="mt-1 text-sm text-slate-400">Privacy, refunds, and terms—customize as needed.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <div className="text-sm font-semibold">Privacy</div>
          <p className="mt-2 text-sm text-slate-400">
            We store customer contact details for order fulfillment.
          </p>
        </Card>
        <Card>
          <div className="text-sm font-semibold">Refunds</div>
          <p className="mt-2 text-sm text-slate-400">
            Refund rules should match your payment provider and business policy.
          </p>
        </Card>
        <Card>
          <div className="text-sm font-semibold">Terms</div>
          <p className="mt-2 text-sm text-slate-400">
            Add your terms of service here.
          </p>
        </Card>
      </div>
    </div>
  )
}
