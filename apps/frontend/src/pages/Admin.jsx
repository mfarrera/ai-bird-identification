import { useNavigate } from 'react-router-dom'
import Layout from '../Layout'

function Admin() {
  const navigate = useNavigate()

  const accions = [
    { label: 'Crear usuari', path: '/admin/crear-usuari' },
    { label: 'Crear admin', path: '/admin/crear-admin' },
    { label: 'Eliminar usuari', path: '/admin/eliminar-usuari' },
    { label: 'Eliminar càmera', path: '/admin/eliminar-camera' },
    { label: 'Afegir càmera', path: '/admin/afegir-camera' },
    { label: 'Enviar detecció a validar', path: '/admin/enviar-deteccio-validar' },
    { label: 'Provar stream amb token', path: '/admin/prova-token-stream' },
    { label: 'Veure càmeres', path: '/admin/cameres' },
    { label: 'Notificacions de càmeres', path: '/admin/notificacions-cameres' }
  ]

  return (
    <Layout
      title="Panell d'administració"
      subtitle="Gestiona usuaris, càmeres i comunitats."
    >
      <div className="admin-grid">
        {accions.map((a) => (
          <div className="admin-card" key={a.path} onClick={() => navigate(a.path)}>
            {a.label}
          </div>
        ))}
      </div>

      <div className="btn-row">
        <button className="btn" onClick={() => navigate('/principal')}>
          Tornar al dashboard
        </button>
      </div>
    </Layout>
  )
}

export default Admin
