/**
 * Shared chrome: fixed Navbar + Footer.
 */
import { Outlet } from 'react-router-dom'
import Navbar from './Navbar.jsx'
import Footer from './Footer.jsx'

export default function Layout() {
  return (
    <div className="flex min-h-screen flex-col bg-cream">
      <Navbar />
      <main className="w-full flex-1 pt-16">
        <Outlet />
      </main>
      <Footer />
    </div>
  )
}
