import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Layout from '../Layout'

const API_URL = 'http://127.0.0.1:8000'

function LlistarCameresAdmin() {
  const [cameres, setCameres] = useState([])
  const [error, setError] = useState('')
  const [missatge, setMissatge] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    const usuariGuardat = localStorage.getItem('usuari')
    const token = localStorage.getItem('token')

    if (!usuariGuardat || !token) {
      navigate('/')
      return
    }

    const usuari = JSON.parse(usuariGuardat)

    if (usuari.role !== 'admin') {
      navigate('/principal')
      return
    }

    const carregarCameres = async () => {
      try {
        setError('')
        setMissatge('Carregant càmeres...')

        const res = await fetch(`${API_URL}/api/cameras`, {
          headers: {
            Authorization: `Bearer ${token}`
          }
        })

        const data = await res.json()

        if (!res.ok) {
          throw new Error(data.detail || 'Error carregant les càmeres')
        }

        setCameres(data)
        setMissatge('')
      } catch (err) {
        setError(err.message)
        setMissatge('')
      }
    }

    carregarCameres()
  }, [navigate])

  return (
    <Layout
      title="Llista de càmeres"
      subtitle="Totes les càmeres registrades a la plataforma."
    >
      <div className="panel">
        {error && <div className="alert alert-error">{error}</div>}
        {missatge && <p className="muted">{missatge}</p>}
        {cameres.length === 0 && !error && <p className="muted">No hi ha càmeres.</p>}

        <div className="entity-list">
          {cameres.map((camera) => (
            <div className="entity-card" key={camera.id}>
              <p><strong>ID:</strong> {camera.id}</p>
              <p><strong>URL:</strong> {camera.url}</p>
              <p><strong>Owner ID:</strong> {camera.owner_id}</p>
              <p><strong>Latitud:</strong> {camera.latitude}</p>
              <p><strong>Longitud:</strong> {camera.longitude}</p>

              <div className="btn-row">
                <button
                  className="btn btn-primary"
                  onClick={() => navigate(`/admin/camera/${camera.id}/stream`)}
                >
                  Veure stream
                </button>
              </div>
            </div>
          ))}
        </div>

        <div className="btn-row">
          <button className="btn" onClick={() => navigate('/admin')}>
            Tornar al panell admin
          </button>
        </div>
      </div>
    </Layout>
  )
}

export default LlistarCameresAdmin
