import { Outlet } from 'react-router-dom'
import Footer from './Footer'
import NavBar from './NavBar'

export default function SiteShell() {
  return (
    <div className="min-h-dvh bg-slate-950">
      <div className="pointer-events-none fixed inset-0 bg-grid opacity-30" />
      <div className="pointer-events-none fixed inset-0 bg-gradient-to-b from-indigo-500/10 via-transparent to-fuchsia-500/10" />

      <div className="relative">
        <NavBar />
        <main className="mx-auto w-full max-w-6xl px-4 py-10">
          <Outlet />
        </main>
        <Footer />
      </div>
    </div>
  )
}