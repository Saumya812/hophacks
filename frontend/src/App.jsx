/**
 * FindMyPal — root router.
 */
import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import Home from './pages/Home.jsx'
import PersonProfile from './pages/PersonProfile.jsx'
import Report from './pages/Report.jsx'
import Tip from './pages/Tip.jsx'
import Lookup from './pages/Lookup.jsx'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Home />} />
        <Route path="/person/:id" element={<PersonProfile />} />
        <Route path="/report" element={<Report />} />
        <Route path="/tip/:id" element={<Tip />} />
        <Route path="/lookup" element={<Lookup />} />
      </Route>
    </Routes>
  )
}
