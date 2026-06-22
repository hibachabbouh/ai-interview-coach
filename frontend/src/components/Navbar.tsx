import { NavLink } from 'react-router-dom'
import './Navbar.css'

export default function Navbar() {
  return (
    <nav className="navbar">
      <div className="container navbar-inner">
        <NavLink to="/" className="navbar-brand">
          <span className="brand-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2a5 5 0 1 0 5 5" />
              <path d="M9 9H5a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-8a2 2 0 0 0-2-2h-4" />
              <circle cx="12" cy="17" r="1" />
            </svg>
          </span>
          <span className="brand-name">
            <span className="grad-text">AI</span> Interview Coach
          </span>
        </NavLink>

        <div className="navbar-links">
          <NavLink to="/interview" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            Interview
          </NavLink>
        </div>

        <NavLink to="/interview" className="btn btn-primary btn-sm">
          Start Session
        </NavLink>
      </div>
    </nav>
  )
}
