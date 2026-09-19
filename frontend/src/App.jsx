/**
 * FindMyPal — root router.
 */
import { useEffect } from 'react'
import { Routes, Route, useLocation } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import Home from './pages/Home.jsx'
import PersonProfile from './pages/PersonProfile.jsx'
import Report from './pages/Report.jsx'
import Tip from './pages/Tip.jsx'
import Lookup from './pages/Lookup.jsx'
import Dashboard from './pages/Dashboard.jsx'

function ScrollToTop() {
  const { pathname } = useLocation()
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }, [pathname])
  return null
}

export default function App() {
  return (
    <>
      <ScrollToTop />
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Home />} />
          <Route path="/person/:id" element={<PersonProfile />} />
          <Route path="/report" element={<Report />} />
          <Route path="/tip/:id" element={<Tip />} />
          <Route path="/lookup" element={<Lookup />} />
          <Route path="/dashboard" element={<Dashboard />} />
        </Route>
      </Routes>
    </>
  )
}
