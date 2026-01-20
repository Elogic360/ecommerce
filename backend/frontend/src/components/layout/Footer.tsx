import { Link } from 'react-router-dom'

export default function Footer() {
  return (
    <footer className="border-t border-white/10">
      <div className="mx-auto grid max-w-6xl gap-6 px-4 py-10 md:grid-cols-3">
        <div>
          <div className="text-sm font-semibold">Vibe Store</div>
          <p className="mt-2 text-sm text-slate-400">
            A clean commerce foundation with React + FastAPI.
          </p>
        </div>
        <div className="text-sm">
          <div className="font-semibold">Company</div>
          <div className="mt-2 grid gap-1 text-slate-400">
            <Link className="hover:text-white" to="/about">
              About
            </Link>
            <Link className="hover:text-white" to="/contact">
              Contact
            </Link>
            <Link className="hover:text-white" to="/policies">
              Policies
            </Link>
          </div>
        </div>
        <div className="text-sm">
          <div className="font-semibold">Admin</div>
          <p className="mt-2 text-slate-400">Use the admin section to manage products and orders.</p>
        </div>
      </div>
      <div className="border-t border-white/10 py-4">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 text-xs text-slate-500">
          <span>© {new Date().getFullYear()} Vibe Store</span>
          <span>Built with React • Tailwind • FastAPI</span>
        </div>
      </div>
    </footer>
  )
}