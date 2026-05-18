import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Admin from './Admin'

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

  const tancarSessio = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('usuari')
    navigate('/')
  }

  return (
    <div style={{ padding: '30px', fontFamily: 'Arial' }}>
      <h1>Llista de càmeres</h1>

      {error && <p style={{ color: 'red' }}>{error}</p>}
      {missatge && <p>{missatge}</p>}

      {cameres.length === 0 && !error && <p>No hi ha càmeres.</p>}

      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', maxWidth: '800px' }}>
        {cameres.map((camera) => (
          <div
            key={camera.id}
            style={{
              border: '1px solid #ccc',
              borderRadius: '8px',
              padding: '15px'
            }}
          >
            <p><strong>ID:</strong> {camera.id}</p>
            <p><strong>URL:</strong> {camera.url}</p>
            <p><strong>Owner ID:</strong> {camera.owner_id}</p>
            <p><strong>Latitud:</strong> {camera.latitude}</p>
            <p><strong>Longitud:</strong> {camera.longitude}</p>

            <button onClick={() => navigate(`/admin/camera/${camera.id}/stream`)}>
              Veure stream
            </button>
          </div>
        ))}
      </div>

      <div style={{ marginTop: '20px' }}>
        <button onClick={() => navigate('/admin')}>Tornar al panell admin</button>
        <button onClick={tancarSessio} style={{ marginLeft: '10px' }}>
          Tancar sessió
        </button>
      </div>
    </div>
  )
}

export default LlistarCameresAdmin