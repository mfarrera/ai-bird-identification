import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Layout from '../Layout'

const API_URL = 'http://127.0.0.1:8000'

function CrearComunitat() {
  const navigate = useNavigate()

  const [name, setName] = useState('')
  const [cameras, setCameras] = useState([])
  const [selectedCameras, setSelectedCameras] = useState([])
  const [error, setError] = useState('')
  const [missatge, setMissatge] = useState('')
  const [loadingCameras, setLoadingCameras] = useState(false)
  const [creating, setCreating] = useState(false)

  const getToken = () => localStorage.getItem('token')

  const carregarCameres = async () => {
    try {
      setError('')
      setLoadingCameras(true)

      const res = await fetch(`${API_URL}/api/cameras`, {
        headers: {
          Authorization: `Bearer ${getToken()}`
        }
      })

      const data = await res.json()

      if (!res.ok) {
        throw new Error(data.detail || 'Error carregant les càmeres')
      }

      setCameras(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoadingCameras(false)
    }
  }

  const toggleCamera = (camera) => {
    const exists = selectedCameras.some((c) => c.id === camera.id)

    if (exists) {
      setSelectedCameras(selectedCameras.filter((c) => c.id !== camera.id))
    } else {
      setSelectedCameras([...selectedCameras, camera])
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setMissatge('')

    if (!name.trim()) {
      setError('Has d’introduir un nom de comunitat')
      return
    }

    try {
      setCreating(true)

      const createRes = await fetch(`${API_URL}/api/communities`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`
        },
        body: JSON.stringify({ name })
      })

      const createData = await createRes.json()

      if (!createRes.ok) {
        throw new Error(createData.detail || 'Error creant la comunitat')
      }

      const communityId = createData.community.id

      if (selectedCameras.length > 0) {
        const camerasRes = await fetch(`${API_URL}/api/communities/${communityId}/cameras`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${getToken()}`
          },
          body: JSON.stringify({
            camera_ids: selectedCameras.map((c) => c.id)
          })
        })

        const camerasData = await camerasRes.json()

        if (!camerasRes.ok) {
          throw new Error(camerasData.detail || 'Error afegint càmeres')
        }
      }

      setMissatge('Comunitat creada correctament. Ets el líder.')
      setName('')
      setSelectedCameras([])
    } catch (err) {
      setError(err.message)
    } finally {
      setCreating(false)
    }
  }

  return (
    <Layout title="Crear comunitat" subtitle="Et convertiràs en el líder de la comunitat que creïs.">
      <div className="panel">
        {error && <div className="alert alert-error">{error}</div>}
        {missatge && <div className="alert alert-success">{missatge}</div>}

        <form onSubmit={handleSubmit}>
          <div className="field">
            <label>Nom de la comunitat</label>
            <input
              className="input wide"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>

          <p className="muted">
            Un cop creada, la resta d'usuaris s'hi podran unir ells mateixos
            des de la llista de comunitats.
          </p>

          <div className="field">
            <h3>Càmeres</h3>
            <button type="button" className="btn" onClick={carregarCameres}>
              Carregar càmeres
            </button>

            {loadingCameras && <p className="muted">Carregant càmeres...</p>}

            {cameras.length > 0 && (
              <div className="entity-list" style={{ marginTop: '12px' }}>
                {cameras.map((camera) => {
                  const checked = selectedCameras.some((c) => c.id === camera.id)

                  return (
                    <label className="entity-card checkbox-row" key={camera.id}>
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => toggleCamera(camera)}
                      />
                      <span>Càmera {camera.id} - {camera.url}</span>
                    </label>
                  )
                })}
              </div>
            )}
          </div>

          <button className="btn btn-primary" type="submit" disabled={creating}>
            {creating ? 'Creant...' : 'Crear comunitat'}
          </button>
        </form>

        <div className="btn-row">
          <button className="btn" onClick={() => navigate('/comunitats')}>
            Tornar a comunitats
          </button>
        </div>
      </div>
    </Layout>
  )
}

export default CrearComunitat
