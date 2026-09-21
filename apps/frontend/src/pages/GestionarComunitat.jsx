import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import Layout from '../Layout'

const API_URL = 'http://127.0.0.1:8000'

function GestionarComunitat() {
  const { communityId } = useParams()
  const navigate = useNavigate()

  const [community, setCommunity] = useState(null)
  const [error, setError] = useState('')
  const [missatge, setMissatge] = useState('')

  const [leaderSearchEmail, setLeaderSearchEmail] = useState('')
  const [leaderSearchResults, setLeaderSearchResults] = useState([])
  const [selectedNewLeader, setSelectedNewLeader] = useState(null)

  const [allCameras, setAllCameras] = useState([])
  const [selectedCameraIds, setSelectedCameraIds] = useState([])

  const token = localStorage.getItem('token')

  const carregarComunitat = async () => {
    try {
      setError('')
      const res = await fetch(`${API_URL}/api/communities/${communityId}`, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      })

      const data = await res.json()

      if (!res.ok) {
        throw new Error(data.detail || 'Error carregant comunitat')
      }

      setCommunity(data)
    } catch (err) {
      setError(err.message)
    }
  }

  useEffect(() => {
    carregarComunitat()
  }, [communityId])

  const buscarNouLider = async () => {
    try {
      setError('')
      setMissatge('')

      const res = await fetch(
        `${API_URL}/api/users/search?email=${encodeURIComponent(leaderSearchEmail)}`,
        {
          headers: {
            Authorization: `Bearer ${token}`
          }
        }
      )

      const data = await res.json()

      if (!res.ok) {
        throw new Error(data.detail || 'Error cercant usuaris')
      }

      setLeaderSearchResults(Array.isArray(data) ? data : [])
    } catch (err) {
      setError(err.message)
    }
  }

  const canviarLider = async () => {
    try {
      setError('')
      setMissatge('')

      if (!selectedNewLeader) {
        throw new Error('Has de seleccionar un nou líder')
      }

      const res = await fetch(`${API_URL}/api/communities/${communityId}/leader`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          leader_id: selectedNewLeader.id
        })
      })

      const data = await res.json()

      if (!res.ok) {
        throw new Error(data.detail || 'Error canviant líder')
      }

      setMissatge('Líder actualitzat correctament')
      setLeaderSearchEmail('')
      setLeaderSearchResults([])
      setSelectedNewLeader(null)
      carregarComunitat()
    } catch (err) {
      setError(err.message)
    }
  }

  const eliminarUsuari = async (userId) => {
    try {
      setError('')
      setMissatge('')

      const res = await fetch(`${API_URL}/api/communities/${communityId}/members/${userId}`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${token}`
        }
      })

      const data = await res.json()

      if (!res.ok) {
        throw new Error(data.detail || 'Error eliminant usuari')
      }

      setMissatge('Usuari eliminat correctament')
      carregarComunitat()
    } catch (err) {
      setError(err.message)
    }
  }

  const carregarCameres = async () => {
    try {
      setError('')
      const res = await fetch(`${API_URL}/api/cameras`, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      })

      const data = await res.json()

      if (!res.ok) {
        throw new Error(data.detail || 'Error carregant càmeres')
      }

      setAllCameras(Array.isArray(data) ? data : [])
    } catch (err) {
      setError(err.message)
    }
  }

  const toggleCamera = (cameraId) => {
    const exists = selectedCameraIds.includes(cameraId)

    if (exists) {
      setSelectedCameraIds(selectedCameraIds.filter((id) => id !== cameraId))
    } else {
      setSelectedCameraIds([...selectedCameraIds, cameraId])
    }
  }

  const afegirCameres = async () => {
    try {
      setError('')
      setMissatge('')

      const res = await fetch(`${API_URL}/api/communities/${communityId}/cameras`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          camera_ids: selectedCameraIds
        })
      })

      const data = await res.json()

      if (!res.ok) {
        throw new Error(data.detail || 'Error afegint càmeres')
      }

      setMissatge('Càmeres afegides correctament')
      setSelectedCameraIds([])
      carregarComunitat()
    } catch (err) {
      setError(err.message)
    }
  }

  const eliminarCamera = async (cameraId) => {
    try {
      setError('')
      setMissatge('')

      const res = await fetch(`${API_URL}/api/communities/${communityId}/cameras/${cameraId}`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${token}`
        }
      })

      const data = await res.json()

      if (!res.ok) {
        throw new Error(data.detail || 'Error eliminant càmera')
      }

      setMissatge('Càmera eliminada correctament')
      carregarComunitat()
    } catch (err) {
      setError(err.message)
    }
  }

  const eliminarComunitat = async () => {
    const confirmat = window.confirm('Segur que vols eliminar aquesta comunitat?')

    if (!confirmat) return

    try {
      setError('')
      setMissatge('')

      const res = await fetch(`${API_URL}/api/communities/${communityId}`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${token}`
        }
      })

      const data = await res.json()

      if (!res.ok) {
        throw new Error(data.detail || 'Error eliminant comunitat')
      }

      navigate('/comunitats')
    } catch (err) {
      setError(err.message)
    }
  }

  if (!community) {
    return (
      <Layout title="Gestionar comunitat">
        <div className="panel">
          {error ? (
            <div className="alert alert-error">{error}</div>
          ) : (
            <p className="muted">Carregant comunitat...</p>
          )}
        </div>
      </Layout>
    )
  }

  return (
    <Layout title="Gestionar comunitat" subtitle={community.name}>
      {error && <div className="alert alert-error">{error}</div>}
      {missatge && <div className="alert alert-success">{missatge}</div>}

      <div className="panel">
        <p><strong>ID:</strong> {community.id}</p>
        <p><strong>Nom:</strong> {community.name}</p>
        <p>
          <strong>Líder:</strong>{' '}
          {community.leader ? community.leader.mail : 'Sense líder'}
        </p>
      </div>

      <div className="panel">
        <h2>Canviar líder</h2>
        <p className="muted" style={{ marginTop: 0 }}>
          Només el líder actual pot transferir el lideratge.
        </p>

        <div className="btn-row">
          <input
            className="input wide"
            type="text"
            value={leaderSearchEmail}
            onChange={(e) => setLeaderSearchEmail(e.target.value)}
            placeholder="Buscar usuari per email"
          />
          <button className="btn" onClick={buscarNouLider}>Cercar</button>
        </div>

        {leaderSearchResults.length > 0 && (
          <div className="entity-list" style={{ marginTop: '12px' }}>
            {leaderSearchResults.map((user) => (
              <div className="entity-row" key={user.id}>
                <div className="entity-info">
                  <div className="title">{user.mail}</div>
                  <div className="meta">{user.role}</div>
                </div>
                <button className="btn" onClick={() => setSelectedNewLeader(user)}>
                  Seleccionar
                </button>
              </div>
            ))}
          </div>
        )}

        <p className="muted" style={{ marginTop: '12px' }}>
          <strong>Nou líder seleccionat:</strong>{' '}
          {selectedNewLeader ? selectedNewLeader.mail : 'Cap'}
        </p>

        <div className="btn-row">
          <button className="btn btn-primary" onClick={canviarLider}>
            Canviar líder
          </button>
        </div>
      </div>

      <div className="panel">
        <h2>Usuaris</h2>
        <p className="muted" style={{ marginTop: 0 }}>
          Els usuaris s'uneixen ells mateixos des de la llista de comunitats.
          Aquí només pots treure membres (si ets el líder).
        </p>

        {community.members.length === 0 && <p className="muted">No hi ha membres.</p>}

        <div className="entity-list">
          {community.members.map((member) => (
            <div className="entity-row" key={member.id}>
              <div className="entity-info">
                <div className="title">{member.mail}</div>
                <div className="meta">{member.role}</div>
              </div>
              <button className="btn btn-danger" onClick={() => eliminarUsuari(member.id)}>
                Eliminar
              </button>
            </div>
          ))}
        </div>
      </div>

      <div className="panel">
        <h2>Càmeres</h2>

        {community.cameras.length === 0 && (
          <p className="muted">No hi ha càmeres associades.</p>
        )}

        <div className="entity-list">
          {community.cameras.map((camera) => (
            <div className="entity-row" key={camera.id}>
              <div className="entity-info">
                <div className="title">Càmera {camera.id}</div>
                <div className="meta">{camera.url}</div>
              </div>
              <button className="btn btn-danger" onClick={() => eliminarCamera(camera.id)}>
                Eliminar
              </button>
            </div>
          ))}
        </div>

        <hr className="divider" />

        <h3>Afegir càmeres</h3>
        <p className="muted" style={{ marginTop: 0 }}>
          Cal ser membre de la comunitat per afegir-hi càmeres.
        </p>
        <button className="btn" onClick={carregarCameres}>Carregar càmeres</button>

        <div className="entity-list" style={{ marginTop: '12px' }}>
          {allCameras.map((camera) => (
            <label className="entity-card checkbox-row" key={camera.id}>
              <input
                type="checkbox"
                checked={selectedCameraIds.includes(camera.id)}
                onChange={() => toggleCamera(camera.id)}
              />
              <span>Càmera {camera.id} - {camera.url}</span>
            </label>
          ))}
        </div>

        {allCameras.length > 0 && (
          <div className="btn-row">
            <button className="btn btn-primary" onClick={afegirCameres}>
              Afegir càmeres seleccionades
            </button>
          </div>
        )}
      </div>

      <div className="btn-row">
        <button className="btn" onClick={() => navigate('/comunitats')}>
          Tornar a la llista de comunitats
        </button>
        <button className="btn btn-danger" onClick={eliminarComunitat}>
          Eliminar comunitat
        </button>
      </div>
    </Layout>
  )
}

export default GestionarComunitat
