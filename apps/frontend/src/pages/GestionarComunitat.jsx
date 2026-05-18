import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

const API_URL = 'http://127.0.0.1:8000'

function GestionarComunitat() {
  const { communityId } = useParams()
  const navigate = useNavigate()

  const [community, setCommunity] = useState(null)
  const [error, setError] = useState('')
  const [missatge, setMissatge] = useState('')

  const [searchEmail, setSearchEmail] = useState('')
  const [userResults, setUserResults] = useState([])

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

  const buscarUsuaris = async () => {
    try {
      setError('')
      setMissatge('')

      const res = await fetch(
        `${API_URL}/api/users/search?email=${encodeURIComponent(searchEmail)}`,
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

      setUserResults(Array.isArray(data) ? data : [])
    } catch (err) {
      setError(err.message)
    }
  }

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

  const afegirUsuari = async (userId) => {
    try {
      setError('')
      setMissatge('')

      const res = await fetch(`${API_URL}/api/communities/${communityId}/members`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          user_ids: [userId]
        })
      })

      const data = await res.json()

      if (!res.ok) {
        throw new Error(data.detail || 'Error afegint usuari')
      }

      setMissatge('Usuari afegit correctament')
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

      navigate('/admin/comunitats')
    } catch (err) {
      setError(err.message)
    }
  }

  if (!community) {
    return (
      <div style={{ padding: '30px', fontFamily: 'Arial' }}>
        {error ? <p style={{ color: 'red' }}>{error}</p> : <p>Carregant comunitat...</p>}
      </div>
    )
  }

  return (
    <div style={{ padding: '30px', fontFamily: 'Arial' }}>
      <h1>Gestionar comunitat</h1>

      {error && <p style={{ color: 'red' }}>{error}</p>}
      {missatge && <p style={{ color: 'green' }}>{missatge}</p>}

      <div style={{ border: '1px solid #ccc', padding: '15px', borderRadius: '8px', marginBottom: '20px' }}>
        <p><strong>ID:</strong> {community.id}</p>
        <p><strong>Nom:</strong> {community.name}</p>
        <p><strong>Líder:</strong> {community.leader ? community.leader.mail : 'Sense líder'}</p>
      </div>

      <div style={{ marginBottom: '25px' }}>
        <h3>Canviar líder</h3>

        <input
          type="text"
          value={leaderSearchEmail}
          onChange={(e) => setLeaderSearchEmail(e.target.value)}
          placeholder="Buscar usuari per email"
        />
        <button onClick={buscarNouLider} style={{ marginLeft: '10px' }}>
          Cercar
        </button>

        {leaderSearchResults.length > 0 && (
          <div style={{ marginTop: '15px' }}>
            {leaderSearchResults.map((user) => (
              <div key={user.id} style={{ marginBottom: '10px' }}>
                {user.mail} ({user.role})
                <button
                  onClick={() => setSelectedNewLeader(user)}
                  style={{ marginLeft: '10px' }}
                >
                  Seleccionar
                </button>
              </div>
            ))}
          </div>
        )}

        <div style={{ marginTop: '15px' }}>
          <strong>Nou líder seleccionat:</strong>{' '}
          {selectedNewLeader ? selectedNewLeader.mail : 'Cap'}
        </div>

        <button onClick={canviarLider} style={{ marginTop: '10px' }}>
          Canviar líder
        </button>
      </div>

      <div style={{ marginBottom: '25px' }}>
        <h3>Usuaris</h3>

        {community.members.length === 0 && <p>No hi ha membres.</p>}

        {community.members.map((member) => (
          <div key={member.id} style={{ marginBottom: '10px' }}>
            {member.mail} ({member.role})
            <button
              onClick={() => eliminarUsuari(member.id)}
              style={{ marginLeft: '10px' }}
            >
              Eliminar
            </button>
          </div>
        ))}

        <hr />

        <h4>Afegir usuaris</h4>
        <input
          type="text"
          value={searchEmail}
          onChange={(e) => setSearchEmail(e.target.value)}
          placeholder="Buscar per email"
        />
        <button onClick={buscarUsuaris} style={{ marginLeft: '10px' }}>
          Cercar
        </button>

        {userResults.map((user) => (
          <div key={user.id} style={{ marginTop: '10px' }}>
            {user.mail} ({user.role})
            <button onClick={() => afegirUsuari(user.id)} style={{ marginLeft: '10px' }}>
              Afegir
            </button>
          </div>
        ))}
      </div>

      <div style={{ marginBottom: '25px' }}>
        <h3>Càmeres</h3>

        {community.cameras.length === 0 && <p>No hi ha càmeres associades.</p>}

        {community.cameras.map((camera) => (
          <div key={camera.id} style={{ marginBottom: '10px' }}>
            Càmera {camera.id} - {camera.url}
            <button
              onClick={() => eliminarCamera(camera.id)}
              style={{ marginLeft: '10px' }}
            >
              Eliminar
            </button>
          </div>
        ))}

        <hr />

        <h4>Afegir càmeres</h4>
        <button onClick={carregarCameres}>Carregar càmeres</button>

        {allCameras.map((camera) => (
          <div key={camera.id} style={{ marginTop: '10px' }}>
            <label>
              <input
                type="checkbox"
                checked={selectedCameraIds.includes(camera.id)}
                onChange={() => toggleCamera(camera.id)}
              />
              <span style={{ marginLeft: '8px' }}>
                Càmera {camera.id} - {camera.url}
              </span>
            </label>
          </div>
        ))}

        {allCameras.length > 0 && (
          <div style={{ marginTop: '15px' }}>
            <button onClick={afegirCameres}>Afegir càmeres seleccionades</button>
          </div>
        )}
      </div>

      <div style={{ marginTop: '30px' }}>
        <button onClick={() => navigate('/admin/comunitats')}>
          Tornar a la llista de comunitats
        </button>

        <button
          onClick={eliminarComunitat}
          style={{ marginLeft: '10px', backgroundColor: '#d9534f', color: 'white' }}
        >
          Eliminar comunitat
        </button>
      </div>
    </div>
  )
}

export default GestionarComunitat