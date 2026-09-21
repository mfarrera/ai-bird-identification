import { useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { programarRenovacioSessio, netejarSessio } from './session'

function navClass(isActive) {
  return isActive ? 'nav-item active' : 'nav-item'
}

function Layout({ title, subtitle, children }) {
  const navigate = useNavigate()
  const location = useLocation()
  const usuari = JSON.parse(localStorage.getItem('usuari') || 'null')
  const isAdmin = usuari && usuari.role === 'admin'
  const path = location.pathname

  useEffect(() => {
    programarRenovacioSessio()
  }, [])

  const handleLogout = () => {
    netejarSessio()
    navigate('/')
  }

  return (
    <div className="dashboard">
      <aside className="sidebar">
        <div className="brand"><span>Av<span className="brand-accent">ia</span>ri</span></div>

        <a className={navClass(path === '/principal')} onClick={() => navigate('/principal')}>Dashboard</a>
        <a className={navClass(path === '/admin/afegir-camera')} onClick={() => navigate('/admin/afegir-camera')}>Sol·licitar càmera</a>
        <a className={navClass(path === '/pujar-imatge')} onClick={() => navigate('/pujar-imatge')}>Pujar imatge</a>
        <a className={navClass(path === '/pujar-video')} onClick={() => navigate('/pujar-video')}>Pujar vídeo</a>
        <a className={navClass(path.startsWith('/comunitats') || path === '/crear-comunitat')} onClick={() => navigate('/comunitats')}>Comunitats</a>

        {isAdmin && (
          <>
            <div className="nav-section-title">Administració</div>
            <a className={navClass(path === '/admin')} onClick={() => navigate('/admin')}>Panell admin</a>
          </>
        )}

        <div className="sidebar-bottom">
          <a className="nav-item" onClick={handleLogout}>Tancar sessió</a>
        </div>
      </aside>

      <main className="main">
        {title && (
          <div className="topbar">
            <div>
              <h1>{title}</h1>
              {subtitle && <p>{subtitle}</p>}
            </div>
          </div>
        )}
        {children}
      </main>
    </div>
  )
}

export default Layout
